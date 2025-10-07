# app.py - Backend با قابلیت خواندن ورودی و اجرای منطق های مختلف
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS 
from datetime import datetime, timedelta
import random
import json

# --- داده‌های شبیه‌سازی شده ---
JOBS_DATA = [
    {"id": "J-001", "location": (35.69, 51.38), "duration_min": 120, "time_window": (480, 720), "specialty": "تعویض ترانسفورماتور"},
    {"id": "J-002", "location": (35.72, 51.45), "duration_min": 90, "time_window": (480, 600), "specialty": "تعمیر کابل"},
    {"id": "J-003", "location": (35.65, 51.42), "duration_min": 180, "time_window": (600, 780), "specialty": "تعویض ترانسفورماتور"},
    {"id": "J-004", "location": (35.75, 51.35), "duration_min": 60, "time_window": (720, 840), "specialty": "تعمیر کابل"},
]
TEAMS_DATA = [
    {"id": "T-HO-01", "base_location": (35.70, 51.40), "specialties": ["تعویض ترانسفورماتور", "تعمیر کابل"], "capacity_min": 480},
    {"id": "T-AR-02", "base_location": (35.60, 51.30), "specialties": ["تعمیر کابل"], "capacity_min": 480}
]
# -------------------------------------------

def calculate_dummy_travel_time(loc1, loc2):
    """تابع ساختگی زمان سفر"""
    distance_km = ((loc1[0] - loc2[0])**2 + (loc1[1] - loc2[1])**2)**0.5 * 100
    travel_time_min = int(distance_km * 5)
    return travel_time_min if travel_time_min > 5 else 10

def format_time(minutes):
    """تبدیل دقیقه به فرمت HH:MM"""
    start_of_day = datetime(1, 1, 1, 0, 0, 0)
    time_delta = timedelta(minutes=minutes)
    return (start_of_day + time_delta).strftime("%H:%M")

def create_output_structure(assignments, assignment_type):
    """تابع کمکی برای ساختاردهی خروجی JSON نهایی"""
    final_output = {"team_assignments": [], "type_applied": assignment_type}
    for team_id, data in assignments.items():
        total_travel = sum(job['travel_time_min'] for job in data['route'])
        total_work = sum(job['job_duration_min'] for job in data['route'])
        
        final_output['team_assignments'].append({
            "team_id": team_id,
            "route": data['route'],
            "total_travel_time_min": total_travel,
            "total_work_time_min": total_work,
            "total_duration_min": total_travel + total_work
        })
    return final_output

# --- توابع تخصیص (الگوریتم‌های مختلف) ---

def generate_random_assignment(jobs, teams):
    """۱. تخصیص تصادفی (منطق فعلی)"""
    unassigned_jobs = list(jobs)
    random.shuffle(unassigned_jobs) 
    assignments = {team['id']: {"route": [], "current_time": 480, "current_location": team['base_location']} for team in teams}

    for job in unassigned_jobs:
        team = random.choice(teams)
        team_id = team['id']
        team_assignment = assignments[team_id]
        
        # ... (منطق ساده تخصیص)
        travel_time = calculate_dummy_travel_time(team_assignment['current_location'], job['location'])
        start_time_candidate = team_assignment['current_time'] + travel_time
        start_window, end_window = job['time_window']
        job_start_time = max(start_time_candidate, start_window)
        job_end_time = job_start_time + job['duration_min']
        
        team_assignment['current_time'] = job_end_time
        team_assignment['current_location'] = job['location']
        
        team_assignment['route'].append({
            "job_id": job['id'], "start_time": format_time(job_start_time), "end_time": format_time(job_end_time),
            "travel_time_min": travel_time, "job_duration_min": job['duration_min']
        })
    
    return create_output_structure(assignments, "random")


def generate_shortest_travel_assignment(jobs, teams):
    """۲. تخصیص بر اساس کمترین زمان سفر"""
    # منطق بهبود یافته: انتخاب نزدیکترین کار به موقعیت فعلی تیم
    assignments = {team['id']: {"route": [], "current_time": 480, "current_location": team['base_location']} for team in teams}
    unassigned_jobs = list(jobs)
    
    while unassigned_jobs:
        for team_id, team_assignment in assignments.items():
            if not unassigned_jobs:
                break
                
            # پیدا کردن نزدیکترین کار به موقعیت فعلی تیم
            closest_job = None
            min_travel_time = float('inf')
            
            for job in unassigned_jobs:
                travel_time = calculate_dummy_travel_time(team_assignment['current_location'], job['location'])
                if travel_time < min_travel_time:
                    min_travel_time = travel_time
                    closest_job = job
            
            if closest_job:
                # محاسبه زمان‌بندی
                start_time_candidate = team_assignment['current_time'] + min_travel_time
                start_window, end_window = closest_job['time_window']
                job_start_time = max(start_time_candidate, start_window)
                job_end_time = job_start_time + closest_job['duration_min']
                
                # بررسی محدودیت زمانی
                if job_end_time <= end_window and job_end_time <= 840:  # ساعت 14:00
                    team_assignment['current_time'] = job_end_time
                    team_assignment['current_location'] = closest_job['location']
                    
                    team_assignment['route'].append({
                        "job_id": closest_job['id'], 
                        "start_time": format_time(job_start_time), 
                        "end_time": format_time(job_end_time),
                        "travel_time_min": min_travel_time, 
                        "job_duration_min": closest_job['duration_min']
                    })
                    
                    unassigned_jobs.remove(closest_job)
    
    return create_output_structure(assignments, "shortest_travel")


def generate_balanced_load_assignment(jobs, teams):
    """۳. تخصیص بر اساس توزیع بار متعادل"""
    assignments = {team['id']: {"route": [], "current_time": 480, "current_location": team['base_location']} for team in teams}
    unassigned_jobs = list(jobs)
    
    # مرتب‌سازی کارها بر اساس مدت زمان (کارهای بزرگتر اول)
    unassigned_jobs.sort(key=lambda x: x['duration_min'], reverse=True)
    
    for job in unassigned_jobs:
        # پیدا کردن تیمی با کمترین بار کاری
        min_workload_team = None
        min_total_work = float('inf')
        
        for team in teams:
            team_id = team['id']
            current_workload = sum(j['job_duration_min'] for j in assignments[team_id]['route'])
            if current_workload < min_total_work:
                min_total_work = current_workload
                min_workload_team = team
        
        if min_workload_team:
            team_id = min_workload_team['id']
            team_assignment = assignments[team_id]
            
            travel_time = calculate_dummy_travel_time(team_assignment['current_location'], job['location'])
            start_time_candidate = team_assignment['current_time'] + travel_time
            start_window, end_window = job['time_window']
            job_start_time = max(start_time_candidate, start_window)
            job_end_time = job_start_time + job['duration_min']
            
            # بررسی محدودیت زمانی
            if job_end_time <= end_window and job_end_time <= 840:
                team_assignment['current_time'] = job_end_time
                team_assignment['current_location'] = job['location']
                
                team_assignment['route'].append({
                    "job_id": job['id'], 
                    "start_time": format_time(job_start_time), 
                    "end_time": format_time(job_end_time),
                    "travel_time_min": travel_time, 
                    "job_duration_min": job['duration_min']
                })
    
    return create_output_structure(assignments, "balanced_load")


def generate_multi_team_assignment(jobs, teams):
    """۴. تخصیص با هماهنگی بین گروهی"""
    # برای کارهایی که نیاز به تخصص‌های مختلف دارند
    assignments = {team['id']: {"route": [], "current_time": 480, "current_location": team['base_location']} for team in teams}
    
    # گروه‌بندی کارها بر اساس تخصص
    specialty_jobs = {}
    for job in jobs:
        specialty = job['specialty']
        if specialty not in specialty_jobs:
            specialty_jobs[specialty] = []
        specialty_jobs[specialty].append(job)
    
    # تخصیص کارها به تیم‌های دارای تخصص مربوطه
    for specialty, specialty_jobs_list in specialty_jobs.items():
        # پیدا کردن تیم‌های دارای این تخصص
        qualified_teams = [team for team in teams if specialty in team['specialties']]
        
        if qualified_teams:
            # توزیع کارها بین تیم‌های واجد شرایط
            for i, job in enumerate(specialty_jobs_list):
                team = qualified_teams[i % len(qualified_teams)]
                team_id = team['id']
                team_assignment = assignments[team_id]
                
                travel_time = calculate_dummy_travel_time(team_assignment['current_location'], job['location'])
                start_time_candidate = team_assignment['current_time'] + travel_time
                start_window, end_window = job['time_window']
                job_start_time = max(start_time_candidate, start_window)
                job_end_time = job_start_time + job['duration_min']
                
                if job_end_time <= end_window and job_end_time <= 840:
                    team_assignment['current_time'] = job_end_time
                    team_assignment['current_location'] = job['location']
                    
                    team_assignment['route'].append({
                        "job_id": job['id'], 
                        "start_time": format_time(job_start_time), 
                        "end_time": format_time(job_end_time),
                        "travel_time_min": travel_time, 
                        "job_duration_min": job['duration_min'],
                        "specialty": specialty
                    })
    
    return create_output_structure(assignments, "multi_team")


# --- تنظیمات Flask و مسیرهای وب ---
app = Flask(__name__)
CORS(app) 

# مسیر اصلی (فقط برای تست لوکال)
@app.route('/')
def index():
    return render_template('index.html')

# مسیر برای آپلود فایل اکسل
@app.route('/api/upload-excel', methods=['POST'])
def upload_excel():
    """دریافت فایل اکسل از فرانت‌اند"""
    try:
        # در اینجا منطق پردازش فایل اکسل قرار می‌گیرد
        # فعلاً یک پاسخ نمونه برمی‌گردانیم
        return jsonify({
            "status": "success",
            "message": "فایل با موفقیت دریافت شد",
            "teams": [
                {"id": "T-HO-01", "name": "تیم هوایی ۱", "capacity": 100},
                {"id": "T-AR-02", "name": "تیم زمینی ۲", "capacity": 100},
                {"id": "T-LI-03", "name": "تیم روشنایی ۳", "capacity": 100}
            ]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# 💡 مسیر API اصلی: دریافت ورودی با متد POST
@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        # خواندن پیام ورودی از فرانت‌اند
        request_data = request.get_json()
        allocation_type = request_data.get('allocation_type', 'random')
        
        # خواندن پارامترهای جدید از فرانت‌اند
        planning_week = request_data.get('planning_week', '')
        work_group = request_data.get('work_group', '')
        daily_hours = request_data.get('daily_hours', 6)
        emergency_capacity = request_data.get('emergency_capacity', 10)
        emergency_jobs = request_data.get('emergency_jobs', [])
        
        print(f"دریافت درخواست بهینه‌سازی:")
        print(f"  - نوع تخصیص: {allocation_type}")
        print(f"  - هفته برنامه‌ریزی: {planning_week}")
        print(f"  - گروه کاری: {work_group}")
        print(f"  - ساعات کاری روزانه: {daily_hours}")
        print(f"  - ظرفیت اضطراری: {emergency_capacity}%")
        print(f"  - تعداد کارهای اضطراری: {len(emergency_jobs)}")
        
        # اضافه کردن کارهای اضطراری به لیست کارها (در صورت وجود)
        all_jobs = JOBS_DATA.copy()
        if emergency_jobs:
            for emergency_job in emergency_jobs:
                # ایجاد کار اضطراری ساختگی
                emergency_job_data = {
                    "id": f"EMG-{emergency_job['id']}",
                    "location": (35.68 + random.random() * 0.1, 51.35 + random.random() * 0.1),
                    "duration_min": random.randint(30, 120),
                    "time_window": (480, 720),  # اولویت در صبح
                    "specialty": "کار اضطراری",
                    "priority": "high"
                }
                all_jobs.append(emergency_job_data)
        
        # انتخاب تابع بر اساس پیام دریافتی
        if allocation_type == 'shortest_travel':
            results = generate_shortest_travel_assignment(all_jobs, TEAMS_DATA)
        elif allocation_type == 'balanced_load':
            results = generate_balanced_load_assignment(all_jobs, TEAMS_DATA)
        elif allocation_type == 'multi_team':
            results = generate_multi_team_assignment(all_jobs, TEAMS_DATA)
        else: # پیش‌فرض یا 'random'
            results = generate_random_assignment(all_jobs, TEAMS_DATA)
        
        # اضافه کردن اطلاعات اضافی به پاسخ
        results['planning_info'] = {
            'planning_week': planning_week,
            'work_group': work_group,
            'daily_hours': daily_hours,
            'emergency_capacity': emergency_capacity,
            'total_emergency_jobs': len(emergency_jobs)
        }
        
        return jsonify(results)
        
    except Exception as e:
        print(f"خطا در پردازش درخواست: {str(e)}")
        return jsonify({
            "error": "خطا در پردازش درخواست",
            "message": str(e)
        }), 500

# مسیر سلامت سرویس
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "سرویس فعال است"})

if __name__ == '__main__':
    print("نرم‌افزار نمایشی در حال اجرا است. به http://127.0.0.1:5000/ بروید.")
    app.run(debug=True)
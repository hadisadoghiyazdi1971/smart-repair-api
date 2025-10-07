# app.py - Backend با الگوریتم‌های بهینه‌سازی واقعی
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS 
from datetime import datetime, timedelta
import random
import math

# --- داده‌های شبیه‌سازی شده ---
JOBS_DATA = [
    {"id": "J-001", "location": (35.69, 51.38), "duration_min": 120, "time_window": (480, 720), "specialty": "تعویض ترانسفورماتور", "priority": "normal"},
    {"id": "J-002", "location": (35.72, 51.45), "duration_min": 90, "time_window": (480, 600), "specialty": "تعمیر کابل", "priority": "normal"},
    {"id": "J-003", "location": (35.65, 51.42), "duration_min": 180, "time_window": (600, 780), "specialty": "تعویض ترانسفورماتور", "priority": "normal"},
    {"id": "J-004", "location": (35.75, 51.35), "duration_min": 60, "time_window": (720, 840), "specialty": "تعمیر کابل", "priority": "normal"},
    {"id": "J-005", "location": (35.68, 51.41), "duration_min": 45, "time_window": (480, 660), "specialty": "تعمیر کابل", "priority": "normal"},
    {"id": "J-006", "location": (35.71, 51.39), "duration_min": 150, "time_window": (540, 780), "specialty": "تعویض ترانسفورماتور", "priority": "normal"},
]
TEAMS_DATA = [
    {"id": "T-HO-01", "base_location": (35.70, 51.40), "specialties": ["تعویض ترانسفورماتور", "تعمیر کابل"], "capacity_min": 480},
    {"id": "T-AR-02", "base_location": (35.60, 51.30), "specialties": ["تعمیر کابل"], "capacity_min": 480},
    {"id": "T-LI-03", "base_location": (35.65, 51.35), "specialties": ["تعویض ترانسفورماتور"], "capacity_min": 480}
]
# -------------------------------------------

def calculate_real_travel_time(loc1, loc2):
    """تابع واقعی‌تر برای محاسبه زمان سفر"""
    # فاصله اقلیدسی در مختصات جغرافیایی
    lat1, lon1 = loc1
    lat2, lon2 = loc2
    
    # تبدیل به کیلومتر (تقریبی)
    distance_km = math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2) * 111
    
    # زمان سفر بر اساس ترافیک (دقیقه)
    base_time = distance_km * 3  # 3 دقیقه per km base
    traffic_factor = random.uniform(1.2, 2.0)  # ضریب ترافیک
    travel_time = int(base_time * traffic_factor)
    
    return max(5, min(travel_time, 120))  # بین 5 تا 120 دقیقه

def format_time(minutes):
    """تبدیل دقیقه به فرمت HH:MM"""
    start_of_day = datetime(1, 1, 1, 0, 0, 0)
    time_delta = timedelta(minutes=minutes)
    return (start_of_day + time_delta).strftime("%H:%M")

def create_output_structure(assignments, assignment_type):
    """تابع کمکی برای ساختاردهی خروجی JSON نهایی"""
    final_output = {"team_assignments": [], "type_applied": assignment_type}
    
    total_travel_all = 0
    total_work_all = 0
    team_counts = []
    
    for team_id, data in assignments.items():
        total_travel = sum(job['travel_time_min'] for job in data['route'])
        total_work = sum(job['job_duration_min'] for job in data['route'])
        total_travel_all += total_travel
        total_work_all += total_work
        team_counts.append(len(data['route']))
        
        final_output['team_assignments'].append({
            "team_id": team_id,
            "route": data['route'],
            "total_travel_time_min": total_travel,
            "total_work_time_min": total_work,
            "total_duration_min": total_travel + total_work,
            "job_count": len(data['route'])
        })
    
    # اضافه کردن آمار کلی
    final_output["summary"] = {
        "total_teams": len(assignments),
        "total_travel_time": total_travel_all,
        "total_work_time": total_work_all,
        "average_jobs_per_team": sum(team_counts) / len(team_counts) if team_counts else 0,
        "min_jobs_per_team": min(team_counts) if team_counts else 0,
        "max_jobs_per_team": max(team_counts) if team_counts else 0
    }
    
    return final_output

# --- توابع تخصیص (الگوریتم‌های مختلف) ---

def generate_random_assignment(jobs, teams):
    """۱. تخصیص تصادفی (منطق فعلی)"""
    unassigned_jobs = list(jobs)
    random.shuffle(unassigned_jobs) 
    assignments = {team['id']: {"route": [], "current_time": 480, "current_location": team['base_location']} for team in teams}

    for job in unassigned_jobs:
        # انتخاب تصادفی تیم
        team = random.choice([t for t in teams if job['specialty'] in t['specialties']])
        team_id = team['id']
        team_assignment = assignments[team_id]
        
        travel_time = calculate_real_travel_time(team_assignment['current_location'], job['location'])
        start_time_candidate = team_assignment['current_time'] + travel_time
        start_window, end_window = job['time_window']
        job_start_time = max(start_time_candidate, start_window)
        job_end_time = job_start_time + job['duration_min']
        
        # بررسی امکان تخصیص
        if job_end_time <= min(end_window, 840):  # حداکثر تا ساعت 14:00
            team_assignment['current_time'] = job_end_time
            team_assignment['current_location'] = job['location']
            
            team_assignment['route'].append({
                "job_id": job['id'], 
                "start_time": format_time(job_start_time), 
                "end_time": format_time(job_end_time),
                "travel_time_min": travel_time, 
                "job_duration_min": job['duration_min'],
                "specialty": job['specialty']
            })
    
    return create_output_structure(assignments, "random")


def generate_shortest_travel_assignment(jobs, teams):
    """۲. تخصیص بر اساس کمترین زمان سفر"""
    assignments = {team['id']: {"route": [], "current_time": 480, "current_location": team['base_location']} for team in teams}
    unassigned_jobs = list(jobs)
    
    # اولویت‌بندی کارهای اضطراری
    emergency_jobs = [j for j in unassigned_jobs if j.get('priority') == 'high']
    normal_jobs = [j for j in unassigned_jobs if j.get('priority') != 'high']
    
    # پردازش کارهای اضطراری اول
    for job_list in [emergency_jobs, normal_jobs]:
        for job in job_list:
            best_team = None
            best_travel_time = float('inf')
            best_start_time = float('inf')
            
            # پیدا کردن بهترین تیم برای این کار
            for team in teams:
                if job['specialty'] not in team['specialties']:
                    continue
                    
                team_id = team['id']
                team_assignment = assignments[team_id]
                
                travel_time = calculate_real_travel_time(team_assignment['current_location'], job['location'])
                start_time_candidate = team_assignment['current_time'] + travel_time
                start_window, end_window = job['time_window']
                job_start_time = max(start_time_candidate, start_window)
                job_end_time = job_start_time + job['duration_min']
                
                # بررسی امکان تخصیص و بهترین زمان سفر
                if job_end_time <= min(end_window, 840) and travel_time < best_travel_time:
                    best_team = team
                    best_travel_time = travel_time
                    best_start_time = job_start_time
            
            if best_team:
                team_id = best_team['id']
                team_assignment = assignments[team_id]
                
                travel_time = calculate_real_travel_time(team_assignment['current_location'], job['location'])
                start_time_candidate = team_assignment['current_time'] + travel_time
                start_window, end_window = job['time_window']
                job_start_time = max(start_time_candidate, start_window)
                job_end_time = job_start_time + job['duration_min']
                
                team_assignment['current_time'] = job_end_time
                team_assignment['current_location'] = job['location']
                
                team_assignment['route'].append({
                    "job_id": job['id'], 
                    "start_time": format_time(job_start_time), 
                    "end_time": format_time(job_end_time),
                    "travel_time_min": travel_time, 
                    "job_duration_min": job['duration_min'],
                    "specialty": job['specialty'],
                    "priority": job.get('priority', 'normal')
                })
    
    return create_output_structure(assignments, "shortest_travel")


def generate_balanced_load_assignment(jobs, teams):
    """۳. تخصیص بر اساس توزیع بار متعادل"""
    assignments = {team['id']: {"route": [], "current_time": 480, "current_location": team['base_location']} for team in teams}
    
    # اولویت‌بندی کارها: اضطراری اول، سپس کارهای بزرگ
    emergency_jobs = [j for j in jobs if j.get('priority') == 'high']
    normal_jobs = [j for j in jobs if j.get('priority') != 'high']
    normal_jobs.sort(key=lambda x: x['duration_min'], reverse=True)  # کارهای بزرگتر اول
    
    all_jobs = emergency_jobs + normal_jobs
    
    for job in all_jobs:
        best_team = None
        best_score = float('inf')
        
        for team in teams:
            if job['specialty'] not in team['specialties']:
                continue
                
            team_id = team['id']
            team_assignment = assignments[team_id]
            
            # محاسبه امتیاز بر اساس تعادل بار
            current_workload = sum(j['job_duration_min'] for j in team_assignment['route'])
            current_travel = sum(j['travel_time_min'] for j in team_assignment['route'])
            
            travel_time = calculate_real_travel_time(team_assignment['current_location'], job['location'])
            start_time_candidate = team_assignment['current_time'] + travel_time
            start_window, end_window = job['time_window']
            job_start_time = max(start_time_candidate, start_window)
            job_end_time = job_start_time + job['duration_min']
            
            if job_end_time <= min(end_window, 840):
                # امتیاز = بار کاری فعلی + زمان سفر (برای تعادل)
                score = current_workload + (travel_time * 0.5)
                
                if score < best_score:
                    best_team = team
                    best_score = score
        
        if best_team:
            team_id = best_team['id']
            team_assignment = assignments[team_id]
            
            travel_time = calculate_real_travel_time(team_assignment['current_location'], job['location'])
            start_time_candidate = team_assignment['current_time'] + travel_time
            start_window, end_window = job['time_window']
            job_start_time = max(start_time_candidate, start_window)
            job_end_time = job_start_time + job['duration_min']
            
            team_assignment['current_time'] = job_end_time
            team_assignment['current_location'] = job['location']
            
            team_assignment['route'].append({
                "job_id": job['id'], 
                "start_time": format_time(job_start_time), 
                "end_time": format_time(job_end_time),
                "travel_time_min": travel_time, 
                "job_duration_min": job['duration_min'],
                "specialty": job['specialty'],
                "priority": job.get('priority', 'normal')
            })
    
    return create_output_structure(assignments, "balanced_load")


def generate_multi_team_assignment(jobs, teams):
    """۴. تخصیص با هماهنگی بین گروهی"""
    assignments = {team['id']: {"route": [], "current_time": 480, "current_location": team['base_location']} for team in teams}
    
    # گروه‌بندی کارها بر اساس تخصص و اولویت
    specialty_groups = {}
    for job in jobs:
        specialty = job['specialty']
        if specialty not in specialty_groups:
            specialty_groups[specialty] = []
        specialty_groups[specialty].append(job)
    
    # برای هر تخصص، کارها را بر اساس اولویت مرتب کن
    for specialty in specialty_groups:
        specialty_groups[specialty].sort(key=lambda x: (0 if x.get('priority') == 'high' else 1, x['duration_min']))
    
    # تخصیص کارها با در نظر گرفتن هماهنگی زمانی
    for specialty, job_list in specialty_groups.items():
        qualified_teams = [team for team in teams if specialty in team['specialties']]
        
        for job in job_list:
            best_team = None
            best_start_time = float('inf')
            
            for team in qualified_teams:
                team_id = team['id']
                team_assignment = assignments[team_id]
                
                travel_time = calculate_real_travel_time(team_assignment['current_location'], job['location'])
                start_time_candidate = team_assignment['current_time'] + travel_time
                start_window, end_window = job['time_window']
                job_start_time = max(start_time_candidate, start_window)
                
                if job_start_time < best_start_time and (job_start_time + job['duration_min']) <= min(end_window, 840):
                    best_team = team
                    best_start_time = job_start_time
            
            if best_team:
                team_id = best_team['id']
                team_assignment = assignments[team_id]
                
                travel_time = calculate_real_travel_time(team_assignment['current_location'], job['location'])
                start_time_candidate = team_assignment['current_time'] + travel_time
                start_window, end_window = job['time_window']
                job_start_time = max(start_time_candidate, start_window)
                job_end_time = job_start_time + job['duration_min']
                
                team_assignment['current_time'] = job_end_time
                team_assignment['current_location'] = job['location']
                
                team_assignment['route'].append({
                    "job_id": job['id'], 
                    "start_time": format_time(job_start_time), 
                    "end_time": format_time(job_end_time),
                    "travel_time_min": travel_time, 
                    "job_duration_min": job['duration_min'],
                    "specialty": job['specialty'],
                    "priority": job.get('priority', 'normal')
                })
    
    return create_output_structure(assignments, "multi_team")


# --- تنظیمات Flask و مسیرهای وب ---
app = Flask(__name__)
CORS(app) 

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload-excel', methods=['POST'])
def upload_excel():
    """دریافت فایل اکسل از فرانت‌اند"""
    try:
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

@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        request_data = request.get_json()
        allocation_type = request_data.get('allocation_type', 'random')
        
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
        
        # اضافه کردن کارهای اضطراری به لیست کارها
        all_jobs = JOBS_DATA.copy()
        if emergency_jobs:
            for i, emergency_job in enumerate(emergency_jobs):
                emergency_job_data = {
                    "id": f"EMG-{emergency_job.get('id', i+1)}",
                    "location": (35.68 + random.random() * 0.1, 51.35 + random.random() * 0.1),
                    "duration_min": random.randint(30, 120),
                    "time_window": (480, 660),  # اولویت در صبح برای کارهای اضطراری
                    "specialty": "کار اضطراری",
                    "priority": "high"
                }
                all_jobs.append(emergency_job_data)

        # انتخاب تابع بر اساس نوع تخصیص
        if allocation_type == 'shortest_travel':
            results = generate_shortest_travel_assignment(all_jobs, TEAMS_DATA)
        elif allocation_type == 'balanced_load':
            results = generate_balanced_load_assignment(all_jobs, TEAMS_DATA)
        elif allocation_type == 'multi_team':
            results = generate_multi_team_assignment(all_jobs, TEAMS_DATA)
        else:
            results = generate_random_assignment(all_jobs, TEAMS_DATA)
        
        # اضافه کردن اطلاعات اضافی
        results['planning_info'] = {
            'planning_week': planning_week,
            'work_group': work_group,
            'daily_hours': daily_hours,
            'emergency_capacity': emergency_capacity,
            'total_emergency_jobs': len(emergency_jobs),
            'algorithm_description': get_algorithm_description(allocation_type)
        }
        
        return jsonify(results)
        
    except Exception as e:
        print(f"خطا در پردازش درخواست: {str(e)}")
        return jsonify({
            "error": "خطا در پردازش درخواست",
            "message": str(e)
        }), 500

def get_algorithm_description(algo_type):
    """توضیح هر الگوریتم"""
    descriptions = {
        'random': 'تخصیص تصادفی کارها به تیم‌های واجد شرایط',
        'shortest_travel': 'اولویت‌بندی بر اساس کمترین زمان سفر و کارهای اضطراری',
        'balanced_load': 'توزیع متعادل بار کاری بین تیم‌ها',
        'multi_team': 'هماهنگی بین گروهی برای کارهای چندتخصصی'
    }
    return descriptions.get(algo_type, 'الگوریتم ناشناخته')

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "سرویس فعال است"})

if __name__ == '__main__':
    print("نرم‌افزار نمایشی در حال اجرا است. به http://127.0.0.1:5000/ بروید.")
    app.run(debug=True)
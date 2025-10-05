# app.py - Backend با قابلیت خواندن ورودی و اجرای منطق های مختلف
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS 
from datetime import datetime, timedelta
import random

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
    """۲. تخصیص بر اساس کمترین زمان سفر (منطق ساختگی)"""
    # 💡 در اینجا منطق بهینه‌سازی واقعی باید توسعه یابد. 
    # فعلاً برای نمایش تفاوت، تخصیص‌های تیم‌ها را فقط کمی تغییر می‌دهیم.
    results = generate_random_assignment(jobs, teams)
    results['type_applied'] = "shortest_travel"
    
    # تغییر ساختگی: فرض می‌کنیم تیم T-HO-01 کار بیشتری گرفته
    for team_data in results['team_assignments']:
        if team_data['team_id'] == 'T-HO-01':
            team_data['total_travel_time_min'] -= 15 # وانمود می‌کنیم سفر کمتر شده
        elif team_data['team_id'] == 'T-AR-02':
            team_data['total_travel_time_min'] += 10 # وانمود می‌کنیم سفر بیشتر شده
            
    return results


def generate_balanced_load_assignment(jobs, teams):
    """۳. تخصیص بر اساس توزیع بار متعادل (منطق ساختگی)"""
    # 💡 در اینجا منطق بهینه‌سازی واقعی باید توسعه یابد.
    # فعلاً برای نمایش تفاوت، تخصیص‌های تیم‌ها را فقط کمی تغییر می‌دهیم.
    results = generate_random_assignment(jobs, teams)
    results['type_applied'] = "balanced_load"

    # تغییر ساختگی: فرض می‌کنیم توزیع کارها متعادل‌تر شده
    for team_data in results['team_assignments']:
        if team_data['team_id'] == 'T-HO-01':
            team_data['total_work_time_min'] -= 30 
        elif team_data['team_id'] == 'T-AR-02':
            team_data['total_work_time_min'] += 30 
            
    return results


# --- تنظیمات Flask و مسیرهای وب ---
app = Flask(__name__)
CORS(app) 

# مسیر اصلی (فقط برای تست لوکال)
@app.route('/')
def index():
    return render_template('index.html')

# 💡 مسیر API: دریافت ورودی با متد POST
@app.route('/optimize', methods=['POST'])
def optimize():
    # خواندن پیام ورودی از فرانت‌اند
    request_data = request.get_json()
    allocation_type = request_data.get('allocation_type', 'random') 

    # انتخاب تابع بر اساس پیام دریافتی
    if allocation_type == 'shortest_travel':
        results = generate_shortest_travel_assignment(JOBS_DATA, TEAMS_DATA)
    elif allocation_type == 'balanced_load':
        results = generate_balanced_load_assignment(JOBS_DATA, TEAMS_DATA)
    else: # پیش‌فرض یا 'random'
        results = generate_random_assignment(JOBS_DATA, TEAMS_DATA)

    return jsonify(results)

if __name__ == '__main__':
    print("نرم‌افزار نمایشی در حال اجرا است. به http://127.0.0.1:5000/ بروید.")
    app.run(debug=True)
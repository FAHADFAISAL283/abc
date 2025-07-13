import re

exercise_categories = {
    'Jumping Jacks': 'Cardio',
    'Burpees': 'Cardio',
    'Mountain Climbers': 'Cardio',
    'High Knees': 'Cardio',
    'Butt Kicks': 'Cardio',
    'Skater Hops': 'Cardio',
    'Skater Jumps': 'Cardio',
    'Bear Crawls': 'Cardio',
    'Crab Walk': 'Cardio',
    'Shadow Boxing': 'Cardio',
    'Kickboxing': 'Cardio',
    'Inchworm': 'Cardio',
    'Russian Twists': 'Cardio',
    'Stair Climbing': 'Cardio',
    'Walking': 'Cardio',
    
    'Rope Jump': 'Plyometrics',
    'Star Jumps': 'Plyometrics',
    'Jump Squats': 'Plyometrics',
    'Tuck Jumps': 'Plyometrics',

    'Treadmill': 'Machine Cardio',
    'Cycling': 'Machine Cardio',
    'Elliptical Machine': 'Machine Cardio',
    'Rowing': 'Machine Cardio',

    'Squats': 'Strength – Lower Body',
    'Weighted Squats': 'Strength – Lower Body',
    'Backpack Squats': 'Strength – Lower Body',
    'Pistol Squats': 'Strength – Lower Body',
    'Bulgarian Squats': 'Strength – Lower Body',
    'Lunges': 'Strength – Lower Body',
    'Reverse Lunges': 'Strength – Lower Body',
    'Weighted Lunges': 'Strength – Lower Body',
    'Weighted Reverse Lunges': 'Strength – Lower Body',
    'Step-ups': 'Strength – Lower Body',
    'Deadlift': 'Strength – Lower Body',
    'Leg Press': 'Strength – Lower Body',
    'Glute Bridges': 'Strength – Lower Body',
    'Calf Raises': 'Strength – Lower Body',
    'Leg Extensions': 'Strength – Lower Body',
    'Leg Curls': 'Strength – Lower Body',
    'Wall Sits': 'Strength – Lower Body',

    'Push-ups': 'Strength – Upper Body',
    'Wide Push-ups': 'Strength – Upper Body',
    'Diamond Push-ups': 'Strength – Upper Body',
    'Incline Push-ups': 'Strength – Upper Body',
    'Decline Push-ups': 'Strength – Upper Body',
    'Dips': 'Strength – Upper Body',
    'Tricep Dips': 'Strength – Upper Body',
    'Inverted Rows': 'Strength – Upper Body',
    'Towel Rows': 'Strength – Upper Body',
    'Seated Cable Rows': 'Strength – Upper Body',
    'Barbell Row': 'Strength – Upper Body',
    'T-Bar Rows': 'Strength – Upper Body',
    'Pull-ups': 'Strength – Upper Body',
    'Lat Pulldown': 'Strength – Upper Body',
    'Front Lat Pulldown': 'Strength – Upper Body',
    'Back Lat Pulldown': 'Strength – Upper Body',
    'Dumbbell Flat Bench Press': 'Strength – Upper Body',
    'Dumbbell Incline Bench Press': 'Strength – Upper Body',
    'Dumbbell Decline Bench Press': 'Strength – Upper Body',
    'Barbell Flat Bench Press': 'Strength – Upper Body',
    'Barbell Incline Bench Press': 'Strength – Upper Body',
    'Barbell Decline Bench Press': 'Strength – Upper Body',
    'Close-grip Bench Press': 'Strength – Upper Body',
    'Chest Fly': 'Strength – Upper Body',
    'Flying Dumbbells': 'Strength – Upper Body',
    'Cable Flyes (High to Low)': 'Strength – Upper Body',
    'Cable Flyes (Low to High)': 'Strength – Upper Body',
    'Overhead Dumbbell Press': 'Strength – Upper Body',
    'Shoulder Press': 'Strength – Upper Body',
    'Arnold Press': 'Strength – Upper Body',
    'Lateral Raises': 'Strength – Upper Body',
    'Front Raises': 'Strength – Upper Body',
    'Dumbbell Side Raises': 'Strength – Upper Body',
    'Face Pulls': 'Strength – Upper Body',
    'Bicep Curls': 'Strength – Upper Body',
    'Dumbbell Bicep Curl(Single)': 'Strength – Upper Body',
    'Dumbbell Bicep Curl(Double)': 'Strength – Upper Body',
    'Barbell Bicep Curls': 'Strength – Upper Body',
    'Dumbbell Hammer Curls': 'Strength – Upper Body',
    'Hammer Curls': 'Strength – Upper Body',
    'Preacher Curl': 'Strength – Upper Body',
    'EZ Bar Curl': 'Strength – Upper Body',
    'Reverse Curl': 'Strength – Upper Body',
    'Tricep Pushdown': 'Strength – Upper Body',
    'Overhead Tricep Extension': 'Strength – Upper Body',
    'Skull Crushers' : 'Strength – Upper Body',
    'Farmers Walk': 'Strength – Upper Body',
    'Kettle Swings': 'Strength – Upper Body',
    'Wall Balls': 'Strength – Upper Body',
    'Dumbbell Thrusters': 'Strength – Upper Body',
    'Turkish Get-ups': 'Strength – Upper Body',
    'Battle Ropes': 'Strength – Upper Body',
    'Pull ups': 'Strength – Upper Body',

    'Plank': 'Core',
    'Side Plank': 'Core',
    'Plank Shoulder Taps': 'Core',
    'Crunches': 'Core',
    'Reverse Crunches': 'Core',
    'Bicycle Crunches': 'Core',
    'Leg Raises': 'Core',
    'Flutter Kicks': 'Core',
    'Russian Twists': 'Core',
    'Superman': 'Core',
}


met_values = {
    'Cardio': 10,         # Average MET for cardio exercises
    'Plyometrics': 9,     # Average MET for plyometric exercises
    'Machine Cardio': 7,  # Average MET for machine-based cardio
    'Strength – Lower Body': 5,  # Average MET for lower body strength
    'Strength – Upper Body': 5,  # Average MET for upper body strength
    'Core': 4,            # Average MET for core exercises
}

def parse_repetition(rep:str) -> float:
    txt = str(rep).lower().strip()
    if 'sec' in txt:
        return int(re.findall(r'\d+', txt)[0])
    if 'min' in txt:
        return int(re.findall(r'\d+', txt)[0]) * 60
    if txt.isdigit():
        return int(txt) * 2.5    # Assume 2.5 seconds per rep for simplicity
    return 0


def estimate_calories_burned(exercise: str, sets: int, reps: str, weight: float = 70) -> int:
    category = exercise_categories.get(exercise, 'Cardio')
    met = met_values.get(category, 10)
    duration_secs = parse_repetition(reps)
    total_duration_min = (duration_secs * sets) / 60
    return int(round((met * weight * 3.5 / 200) * total_duration_min))



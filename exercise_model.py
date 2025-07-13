from pymongo import MongoClient  
import pandas as pd
from sklearn.preprocessing import LabelEncoder 
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors
from sklearn.multioutput import MultiOutputClassifier   #we want multiple outputs
import re   #parse data in reps column

#random forest makes forest of decison trees and then uses avg prediction of each tree to make final prediction
#used for clasification tasks

# Connect to MongoDB
client = MongoClient("mongodb+srv://fahad:fahad_123@cluster0.bwyuy.mongodb.net/test?retryWrites=true&w=majority&appName=Cluster0")
db = client["test"]
users_collection = db["questions"]
exercise_collection = db["Exercises"]

# Load exercise and user data
exercise_data = list(exercise_collection.find({}, {"_id": 0}))
exercise_df = pd.DataFrame(exercise_data)
exercise_df.columns = exercise_df.columns.str.strip()

user_data_list = list(users_collection.find({}, {"_id": 0}))
user_df = pd.DataFrame(user_data_list)

# Label encoding
label_encoders = {}
for col in ['Goals', 'Preference']:
    user_df[col] = user_df[col].astype(str).str.strip()
    exercise_df[col] = exercise_df[col].astype(str).str.strip()
    le = LabelEncoder()
    combined_data = pd.concat([user_df[col], exercise_df[col]], ignore_index=True)
    le.fit(combined_data)
    user_df[col] = le.transform(user_df[col])
    exercise_df[col] = le.transform(exercise_df[col])
    label_encoders[col] = le
#to get consistent labelings in both datasets

le_activity = LabelEncoder()
user_df['Activity Level'] = le_activity.fit_transform(user_df['Activity Level'].astype(str))
label_encoders['Activity Level'] = le_activity

le_exercises = LabelEncoder()
exercise_df['Exercises'] = le_exercises.fit_transform(exercise_df['Exercises'].astype(str))
label_encoders['Exercises'] = le_exercises

# KNN setup
knn = NearestNeighbors(n_neighbors=25, metric='euclidean')
knn.fit(exercise_df[['Goals', 'Preference']])

def find_knn_exercise_match(goal, gym_home, n_recommendations=25):
    target_df = pd.DataFrame([[goal, gym_home]], columns=['Goals', 'Preference'])
    indices = knn.kneighbors(target_df, return_distance=False)[0][:n_recommendations]
    return exercise_df.iloc[indices]
#return distance = false means we dont want to know distance, we only want index
#it uses euclidean distance

# Prepare features for training
matched_exercises = user_df.apply(lambda row: find_knn_exercise_match(row['Goals'], row['Preference'], 25), axis=1)
exercise_with_user_features = user_df.copy()
exercise_with_user_features['Exercises'] = matched_exercises.apply(lambda x: list(x['Exercises'].values) if not x.empty else [])

features = ['BMR', 'BMI', 'Goals', 'Preference', 'Activity Level']

X_train, X_test, y_train, y_test = train_test_split(
    exercise_with_user_features[features],
    exercise_with_user_features['Exercises'].apply(pd.Series),
    test_size=0.2, random_state=42
)

#Applying model
rf_model = RandomForestClassifier(n_estimators=10, random_state=42)
multi_output_rf = MultiOutputClassifier(rf_model)
multi_output_rf.fit(X_train, y_train)

def parse_repetition(value):
    if isinstance(value, str):  #check if a value is string
        match = re.search(r'\d+', value)
        if match:
            return f"{match.group()} {value.replace(match.group(), '').strip()}"
        return value
    return str(value)

def exercise_recommendations(user_data, n_exercises=25):
    # Transform user inputs
    for col in ['Goals', 'Preference']:
        if col in user_data:
            user_data[col] = label_encoders[col].transform([user_data[col]])[0]
    if 'Activity Level' in user_data:
        user_data['Activity Level'] = label_encoders['Activity Level'].transform([user_data['Activity Level']])[0]

    # Predict top exercises
    user_features = pd.DataFrame([user_data])[features].astype(float)
    predicted_exercises = multi_output_rf.predict(user_features).flatten().astype(int)
    top_exercises = label_encoders['Exercises'].inverse_transform(predicted_exercises)

    cardio_set = {'Walking', 'Treadmill', 'Cycling', 'Elliptical Machine', 'Stair Climbing'}

    full_plan = {}
    for week in range(1, 5):
        weekly_plan = {f"Day {i+1}": [] for i in range(5)}
        for i, exercise_name in enumerate(top_exercises[:n_exercises]):
            encoded_val = label_encoders['Exercises'].transform([exercise_name])[0]
            matched_ex = exercise_df[exercise_df['Exercises'] == encoded_val].iloc[0]

            # Base sets and reps
            base_sets = int(matched_ex.get('Sets', 0))
            base_reps_str = str(matched_ex.get('Repetition', '0 reps'))
            match_num = re.search(r'\d+', base_reps_str)
            base_reps = int(match_num.group()) if match_num else 0
            unit = re.sub(r'\d+', '', base_reps_str).strip()

            # Determine if exercise is cardio
            is_cardio = exercise_name in cardio_set

            # Adjust sets: cardio retains base sets, others follow week rules
            if is_cardio:
                adjusted_sets = base_sets
            else:
                if week == 1:
                    adjusted_sets = base_sets
                elif week in [2, 3]:
                    adjusted_sets = base_sets
                else:  # week 4
                    adjusted_sets = 4

            # Adjust reps/duration increment
            if is_cardio:
                # Increase time by 2 minutes per week
                reps_increment = 2 * (week - 1)
            else:
                # Non-cardio: week2 +2, week3 +4, week4 +4
                reps_increment = 0 if week == 1 else 2 if week == 2 else 4

            adjusted_reps = f"{base_reps + reps_increment} {unit}" if unit else str(base_reps + reps_increment)

            # Build exercise details
            exercise_details = {
                'Exercises': exercise_name,
                'Sets': adjusted_sets,
                'Repetition': adjusted_reps,
                'Warning': matched_ex.get('Warning', '')
            }

            weekly_plan[f"Day {(i % 5) + 1}"].append(exercise_details)

        full_plan[f"Week {week}"] = weekly_plan

    return full_plan

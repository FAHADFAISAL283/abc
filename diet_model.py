from pymongo import MongoClient
import pandas as pd                  
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors

# Connect to MongoDB
client = MongoClient("mongodb+srv://fahad:fahad_123@cluster0.bwyuy.mongodb.net/test?retryWrites=true&w=majority&appName=Cluster0")
db = client["test"]
users_collection = db["questions"]  # User dataset
food_collection = db["Diet"]  # Food dataset

# Load data from MongoDB
food_data = list(food_collection.find({}, {"_id": 0}))  # Exclude _id
food_df = pd.DataFrame(food_data)
user_data_list = list(users_collection.find({}, {"_id": 0}))  # Exclude _id
user_df = pd.DataFrame(user_data_list)

# Convert categorical fields to numeric
label_encoders = {}
for col in ['BMI Case', 'Activity Level']:
    le = LabelEncoder()
    user_df[col] = le.fit_transform(user_df[col])
    label_encoders[col] = le

# Encode meal names in the food dataset
for column in ['Meal 1 (Breakfast)', 'Meal 2 (Lunch)', 'Meal 3 (Snack)', 'Meal 4 (Dinner)']:
    le = LabelEncoder()
    food_df[column] = le.fit_transform(food_df[column])
    label_encoders[column] = le

# Train a KNN model for calorie matching
knn = NearestNeighbors(n_neighbors=2, metric='euclidean')
knn.fit(food_df[['Calories']])  # Fit KNN on Calories column

def find_knn_meal_match(calorie_target):
    target_df = pd.DataFrame([[calorie_target]], columns=['Calories'])
    index = knn.kneighbors(target_df, return_distance=False)[0][0]
    return food_df.iloc[index]

# Apply KNN function to find matches
matched_food = user_df['Required Calories'].apply(find_knn_meal_match).apply(pd.Series)

# Merge matched food meals into the user dataset
food_with_user_features = user_df.copy()
for column in ['Meal 1 (Breakfast)', 'Meal 2 (Lunch)', 'Meal 3 (Snack)', 'Meal 4 (Dinner)']:
    food_with_user_features[column] = matched_food[column].values

# Define features for training
features = ['Required Calories', 'BMR', 'Total Calorie Intake', 'BMI Case', 'Activity Level']

# Train separate RandomForest models for each meal type
models = {}
for column in ['Meal 1 (Breakfast)', 'Meal 2 (Lunch)', 'Meal 3 (Snack)', 'Meal 4 (Dinner)']:
    X_train, X_test, y_train, y_test = train_test_split(
        food_with_user_features[features], food_with_user_features[column], test_size=0.2, random_state=42
    )
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    models[column] = model  # Store trained model

def get_meal_recommendations(user_data):
    for col in ['BMI Case', 'Activity Level']:
        user_data[col] = label_encoders[col].transform([user_data[col]])[0] 

    user_features = pd.DataFrame([user_data])[features]  # Convert user data to DataFrame
    recommended_meals = {}

    for column, model in models.items():
        predicted_label = model.predict(user_features)[0]
        recommended_meals[column] = label_encoders[column].inverse_transform([predicted_label])[0]

    return recommended_meals

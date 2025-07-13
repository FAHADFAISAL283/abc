import logging
from typing import Any, Dict
from fastapi import FastAPI, HTTPException   #fastapi is a framework used to build apis in python
from diet_model import get_meal_recommendations, users_collection
from exercise_model import exercise_recommendations
from calorie_burn import estimate_calories_burned

from pydantic import BaseModel 
from motor.motor_asyncio import AsyncIOMotorClient   #to interact with mongoDB
from datetime import datetime, UTC
from uuid import uuid4   #gives a 129 bit unique id for each convo 8,4,4,4,12 format in hexadecimal

client = AsyncIOMotorClient("mongodb+srv://fahad:fahad_123@cluster0.bwyuy.mongodb.net/test?retryWrites=true&w=majority&appName=Cluster0")
db = client.test
chat_history_collection = db.chat_history
plans_collection = db.recommended_exercise
questionnaire_collection = db['questions']
user_reviews_collection = db["user_Reviews"]
progress_collection = db["Progress"]


app = FastAPI()     #initialize the app to get routes

# Chat message model
class ChatMessage(BaseModel):
    uid : str
    conversation_id: str
    role: str
    text: str
    timestamp: datetime = datetime.now(UTC)
  
class PlanPayload(BaseModel):
    exercise_plan: Dict[str, Any]

class ReviewModel(BaseModel):
    name : str
    review : str
    rating : str

class BurnLog(BaseModel):
    calories_burned: int
    week: str
    day: str

@app.get("/recommend_meal/{uid}")
def recommend_meals(uid: str):
    try:
        user_data = users_collection.find_one({"UID": uid})
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        recommendations = get_meal_recommendations(user_data)
        return {"UID": uid, "recommendations": recommendations}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recommend_exercise/{uid}")
def recommend_exercise(uid: str):
    try:
        user_data = users_collection.find_one({"UID": uid})
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        recommendations = exercise_recommendations(user_data)
        return {"UID": uid, "exercise_plan": recommendations}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save_chat/")
async def save_chat_message(chat_message: ChatMessage):
    try:
        message_entry = {
            "role": chat_message.role,
            "text": chat_message.text,
            "timestamp": chat_message.timestamp
        }

        result = await chat_history_collection.update_one(
            {"conversation_id": chat_message.conversation_id},
            {
                "$setOnInsert": {   #make sure email and convo_id is set only once
                    "uid": chat_message.uid,
                    "conversation_id": chat_message.conversation_id
                },
                "$push": {"messages": message_entry}
            },
            upsert=True
        )

        return {
            "status": "Message saved successfully",
            "upserted_id": str(result.upserted_id) if result.upserted_id else "updated"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/load_chat/{uid}")
async def load_chat(uid: str):
    try:
        convo = await chat_history_collection.find_one({"uid": uid})
        if not convo or "messages" not in convo:
            return {"uid": uid, "chat_messages": []}  #if no meesages, return empty

        sorted_messages = sorted(
            convo["messages"],
            key=lambda msg: msg.get("timestamp")
        )

        chat_messages = [
            {
                "role": msg["role"],
                "text": msg["text"],
                "timestamp": msg["timestamp"].strftime('%Y-%m-%d %H:%M:%S')
            }
            for msg in sorted_messages
        ]

        return {"uid": uid, "chat_messages": chat_messages}  #return messages according to timestamp

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_conversation_id/{uid}")
async def get_conversation_id(uid: str):
    try:
        existing = await chat_history_collection.find_one({"uid": uid})
        if existing:
            return {"conversation_id": existing["conversation_id"]}
        else:
            new_id = str(uuid4())
            return {"conversation_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/save_exercise_plan/{uid}")
async def upsert_plan(uid: str, payload: PlanPayload):
    try:
        # 1) Fetch user weight
        user_doc = await questionnaire_collection.find_one({"UID": uid})
        if not user_doc:
            raise HTTPException(404, "User questionnaire not found")
        weight = user_doc.get("Weight", 70)

        # 2) Copy and inject calories into each exercise
        updated_plan = {}
        for week, week_data in payload.exercise_plan.items():
            updated_plan[week] = {}
            for day, exercises in week_data.items():
                updated_exs = []
                for ex in exercises:
                    try:
                        name = ex["Exercises"]
                        sets = int(ex["Sets"])
                        reps = str(ex["Repetition"])
                    except KeyError as ke:
                        logging.error(f"Missing key {ke} in exercise doc: {ex}")
                        raise HTTPException(400, f"Malformed exercise entry: missing {ke}")

                    cal = estimate_calories_burned(name, sets, reps, weight)
                    ex["calories_burned"] = cal
                    updated_exs.append(ex)

                updated_plan[week][day] = updated_exs

        # 3) Upsert into Mongo
        plans_collection.update_one(
            {"uid": uid},
            {"$set": {"exercise_plan": updated_plan}},
            upsert=True
        )
        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Failed to save exercise plan")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/get_exercise_status/{uid}")
async def get_exercise_status(uid: str):
    user_data = await plans_collection.find_one({"uid": uid}, {"_id": 0, "exercise_plan": 1})
    if not user_data:
        raise HTTPException(status_code=404, detail="Exercise plan not found for user")

    return user_data

@app.get("/get_progress/{uid}")
async def get_progress(uid: str):
    try:
        user_data = await plans_collection.find_one({"uid": uid})
        if not user_data or "exercise_plan" not in user_data:
            return {"progress": []}

        progress = []
        for week_key, week_value in user_data["exercise_plan"].items():
            for day_key, day_value in week_value.items():
                for ex in day_value:
                    if ex.get("Completed") and ex.get("calories_burned"):
                        progress.append({
                            "week": week_key,
                            "day": day_key,
                            "exercise": ex["Exercises"],
                            "calories_burned": ex["calories_burned"]
                        })
        return {"progress": progress}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reviews")
async def get_reviews():
    try:
        reviews_cursor = user_reviews_collection.find()
        reviews = []
        async for review in reviews_cursor:
            reviews.append({
                "name": review.get("name", ""),
                "review": review.get("review", ""),
                "rating": review.get("rating", "5"),
            })
        return reviews
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# POST a new review
@app.post("/reviews")
async def post_review(review: ReviewModel):
    try:
        review_doc = review.dict()
        await user_reviews_collection.insert_one(review_doc)
        return {"message": "Review saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/log_calories/{uid}")
async def log_calories(uid: str, data: BurnLog):
    try:
        doc = await progress_collection.find_one({"user_id": uid})
        if not doc:
            # Initialize fresh structure with 0 calories
            weeks = []
            for w in range(1, 5):
                days = [{"day": f"Day {d}", "calories_burned": 0} for d in range(1, 6)]
                weeks.append({"week": f"Week {w}", "days": days})
            doc = {
                "user_id": uid,
                "weeks": weeks,
                "updated_at": datetime.utcnow()
            }
            await progress_collection.insert_one(doc)

        # Update the specific week/day
        await progress_collection.update_one(
            {
                "user_id": uid,
                "weeks.week": data.week,
                "weeks.days.day": data.day
            },
            {
                "$inc": {"weeks.$[w].days.$[d].calories_burned": data.calories_burned},
                "$set": {"updated_at": datetime.utcnow()}
            },
            array_filters=[
                {"w.week": data.week},
                {"d.day": data.day}
            ]
        )

        return {"success": True, "message": "Calories logged"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/estimate_goal_duration/{uid}")
async def estimate_goal_duration(uid: str):
    user = await questionnaire_collection.find_one({"UID": uid})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    progress = await progress_collection.find_one({"user_id": uid})
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")

    current_weight = float(user.get("Weight"))
    target_weight = float(user.get("Target Weight"))
    goal = user.get("Goals")

    weight_diff = abs(current_weight - target_weight)
    if weight_diff == 0 or goal == "Stay Fit":
        return {
            "date": None,
            "message": "You're already at your goal. Maintain your progress!"
        }

    total_weeks_needed = weight_diff / 0.5  # 0.5 kg per week

    # Count how many effective weeks based on progress
    completed_weeks = 0.0
    for week in progress.get("weeks", []):
        days = week.get("days", [])
        completed_days = sum(1 for d in days if d.get("calories_burned", 0) > 0)
        week_progress = completed_days / len(days) if days else 0
        completed_weeks += week_progress

    if completed_weeks == 0:
        raise HTTPException(status_code=400, detail="No effective progress yet")

    avg_weekly_progress = completed_weeks / len(progress.get("weeks", []))
    if avg_weekly_progress == 0:
        raise HTTPException(status_code=400, detail="No weekly progress detected")

    # Estimate time to goal based on avg weekly progress
    remaining_weeks = max((total_weeks_needed - completed_weeks), 0)
    estimated_date = datetime.utcnow() + timedelta(weeks=remaining_weeks)
    formatted_date = estimated_date.strftime("%d %B")

    return {
        "date": formatted_date,
        "message": f"You will reach your goal by {formatted_date}."
    }



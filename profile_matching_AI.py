# def AI_Profile_Matching (User_ID): 
# Analyze the user's profile with other users in the database
# Groq AI API will calculate the similarity score between the user's profile and other users' profiles
# Returns Dictionary Band [(85, 100), (70, 85), (70, 50), (50, 0)]

# Profile Database: https://docs.google.com/spreadsheets/d/1N_2QPdtVigDzzmyjlyUB_AIdLArnxbScmLbq0s2UCdU/edit?usp=sharing

import os
from groq import Groq


def AI_Profile_Matching(User_ID):
    client = Groq(
        api_key=os.getenv("PROFILE_MATCHING_API_KEY")
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1000,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful matcher that analyzes user profiles and calculates similarity scores."
            },
            { 
                "role": "user",
                "content": f"Analyze the profile of user with ID {User_ID} and compare it with other users in the database. Return a list of matching scores in the format [(user_id, similarity_score), ...]."
            },
            {
                "role": "user",
                "content": "Sort the matching scores in descending order and categorize them into bands: [(85, 100), (70, 85), (50, 70), (0, 50)]."
            },
        ]
    )

    return response.choices[0].message.content

# def Add_To_Database

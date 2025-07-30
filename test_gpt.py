from openai import OpenAI
from dotenv import load_dotenv
import time
load_dotenv()

client = OpenAI()

model = "gpt-4.1-nano"
image_url = r"https://file.dyhs.kr/B7CC7B9D-0C13-421D-B461-BAE0FE1B0D3F.jpg"
prompt = '''
Analysis of ingredients in food names and food photos, and calorie prediction
Return results in JSON format(language: Korean)
{
    "food_name": "Food Name",
    "ingredients": {
        "Ingredient1": "Calories1",
        "Ingredient2": "Calories2",
        "Ingredient3": "Calories3"
    },
    "total_calories": "Total Calories",
    "analysis": "Analysis and description of the food (prediction basis, reason explanation)"
}
'''

start_time = time.time()
print(f"Request started at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")

stream = client.responses.create(
    model=model,
    input=[
        {"role": "user", "content": prompt},
        {
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": image_url
                }
            ]
        }
    ],
    stream=True
)

for event in stream:
    if hasattr(event, "delta"):
        print(event.delta, end="", flush=True)

end_time = time.time()
print(f"\nRequest completed at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}")
print(f"Total time taken: {end_time - start_time:.2f} seconds")

print("\n")
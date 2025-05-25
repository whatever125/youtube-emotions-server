import os
import re
import emoji
from googleapiclient.discovery import build
from transformers import pipeline
from collections import defaultdict

emotion_model = pipeline(
    "text-classification",
    model="bhadresh-savani/bert-base-uncased-emotion",
    return_all_scores=True
)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

api_service_name = "youtube"
api_version = "v3"
DEVELOPER_KEY = ""

youtube = build(api_service_name, api_version, developerKey=DEVELOPER_KEY)


def get_comments(video_id, max_results):
    comments = []
    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,  # Max per request (API limit)
        textFormat="plainText",
        order="relevance"
    )

    while request and len(comments) < max_results:
        response = request.execute()
        comments.extend([
            item['snippet']['topLevelComment']['snippet']['textDisplay']
            for item in response['items']
        ])

        # Check if there are more comments
        if 'nextPageToken' in response:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                pageToken=response['nextPageToken'],  # Pagination key
                textFormat="plainText",
                order="relevance"
            )
        else:
            break

    return comments[:max_results]


def analyze_emotion(text):
    result = emotion_model(text)[0]
    return result['label'], result['score']


def timestamp_to_seconds(timestamp):
    digits = timestamp.split(':')
    seconds = int(digits[-1]) + 60 * int(digits[-2]) # seconds and minutes
    if len(digits) == 3:
        seconds += 60 * 60 * int(digits[0]) # hours
    return seconds


def get_timestamp(pattern, comment):
    timestamps = pattern.findall(comment)
    if len(timestamps) == 1:
        return timestamps[0]
    return None


def process_comment(comment):
    text = re.sub(r'[^\w\s.,!?:;@#\']', '', comment)  # Оставляет буквы, цифры, пунктуацию
    text = text.lower()  # Приведение к нижнему регистру
    text = re.sub(r'(.)\1{2,}', r'\1', text)  # Исправление повторяющихся символов
    text = emoji.demojize(text)  # Обработка эмодзи
    return text


def filter_comments(comments):
    comments_filtered = []
    pattern = re.compile(r"(?:\d{1,2}:)?\d{1,2}:\d{2}")
    for comment in comments:
        timestamp = get_timestamp(pattern, comment)
        if timestamp is None:
            continue
        text = process_comment(comment)
        results = emotion_model(text)
        for emotion in results[0]:
            if emotion['score'] > 0.5:  # Порог 50%
                comments_filtered.append({'text': text, 'emotion': emotion, 'timestamp': timestamp_to_seconds(timestamp)})
    return comments_filtered


# Function to round timestamp to the nearest 5-second interval
def round_timestamp(timestamp):
    return round(timestamp / 5) * 5


def group_comments_by_time(comments_filtered):
    grouped_comments = defaultdict(list)
    for comment in comments_filtered:
        rounded_timestamp = round_timestamp(comment['timestamp'])
        grouped_comments[rounded_timestamp].append(comment)
    # Convert the defaultdict to a regular dict for easier use
    grouped_comments = dict(grouped_comments)
    return grouped_comments


def get_dominant_emotion(group_of_comments):
    emotion_counts = defaultdict(int)
    for comment in group_of_comments:
        emotion = comment['emotion']['label']
        emotion_counts[emotion] += 1

    max_count = max(emotion_counts.values())
    dominant_emotions = [emotion for emotion, count in emotion_counts.items() if count == max_count]

    if len(dominant_emotions) == 1 and max_count > len(group_of_comments) / 2:
        return dominant_emotions[0]
    else:
        return None


def get_emotional_moments(grouped_comments):
    timestamp_emotion_pairs = []
    for timestamp, comments in grouped_comments.items():
        if len(comments) >= 1:
            dominant_emotion = get_dominant_emotion(comments)
            if dominant_emotion:
                timestamp_emotion_pairs.append((timestamp, dominant_emotion))
    # Print the list of timestamp: emotion pairs
    for timestamp, emotion in timestamp_emotion_pairs:
        print(f"{timestamp}: {emotion}")
    return timestamp_emotion_pairs


def main(video_id, max_results):
    comments = get_comments(video_id, max_results)
    comments_with_timestamp = filter_comments(comments)
    grouped_comments_by_time = group_comments_by_time(comments_with_timestamp)
    emotional_moments = get_emotional_moments(grouped_comments_by_time)
    return sorted(emotional_moments, key=lambda x: x[0])

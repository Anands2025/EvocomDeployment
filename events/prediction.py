import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import CountVectorizer
from .models import EventSuccessMetrics
from django.utils import timezone

def train_prediction_model():
    metrics = EventSuccessMetrics.objects.all()
    
    if not metrics.exists():
        print("No event success metrics found. Please generate some data first.")
        return None, None, None, None, None  # Return 5 None values

    df = pd.DataFrame(list(metrics.values()))
    
    le_event = LabelEncoder()
    le_community_category = LabelEncoder()
    le_community_name = LabelEncoder()
    
    df['event_category'] = le_event.fit_transform(df['event_category'])
    df['community_category'] = le_community_category.fit_transform(df['community_category'])
    df['community_name'] = le_community_name.fit_transform(df['community_name'])
    
    # Convert time to minutes since midnight
    df['start_time_minutes'] = df['start_time'].apply(lambda x: x.hour * 60 + x.minute)
    df['end_time_minutes'] = df['end_time'].apply(lambda x: x.hour * 60 + x.minute)
    
    # Process keywords
    vectorizer = CountVectorizer(max_features=100)
    keyword_features = vectorizer.fit_transform(df['keywords']).toarray()
    keyword_feature_names = vectorizer.get_feature_names_out()
    keyword_df = pd.DataFrame(keyword_features, columns=keyword_feature_names)
    
    # Combine all features
    X = pd.concat([
        df[['event_category', 'community_category', 'community_name', 'start_time_minutes', 
            'end_time_minutes', 'duration_hours', 'is_weekend', 'is_free']],
        keyword_df
    ], axis=1)
    
    y = df['attendance_ratio']
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    score = model.score(X, y)
    print(f"Model R-squared score: {score}")
    
    return model, le_event, le_community_category, le_community_name, vectorizer

def predict_event_success(event_category, community_category, community_name, start_time, end_time, description, is_free):
    model, le_event, le_community_category, le_community_name, vectorizer = train_prediction_model()
    
    if model is None:
        return None

    # Convert time to minutes since midnight
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    
    # Calculate duration in hours
    duration_hours = (end_minutes - start_minutes) / 60
    
    # Determine if it's a weekend (assuming start_time is a datetime object)
    is_weekend = start_time.weekday() >= 5 if isinstance(start_time, timezone.datetime) else False
    
    # Handle unseen categories
    try:
        event_category_encoded = le_event.transform([event_category])[0]
    except ValueError:
        event_category_encoded = -1

    try:
        community_category_encoded = le_community_category.transform([community_category])[0]
    except ValueError:
        community_category_encoded = -1

    try:
        community_name_encoded = le_community_name.transform([community_name])[0]
    except ValueError:
        community_name_encoded = -1
    
    # Process keywords
    keywords = ' '.join(description.split()[:10])  # Use first 10 words as keywords
    keyword_features = vectorizer.transform([keywords]).toarray()
    
    # Combine all features
    input_data = pd.DataFrame({
        'event_category': [event_category_encoded],
        'community_category': [community_category_encoded],
        'community_name': [community_name_encoded],
        'start_time_minutes': [start_minutes],
        'end_time_minutes': [end_minutes],
        'duration_hours': [duration_hours],
        'is_weekend': [is_weekend],
        'is_free': [is_free]
    })
    
    keyword_df = pd.DataFrame(keyword_features, columns=vectorizer.get_feature_names_out())
    input_data = pd.concat([input_data, keyword_df], axis=1)
    
    # Make prediction
    prediction = model.predict(input_data)
    
    return prediction[0]
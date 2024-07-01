import joblib

#model = joblib.load('model/time_predictor_model.pkl')
#scaler = joblib.load('model/scaler.pkl')


#async def predict_time(duration):
#    duration_scaled = scaler.transform([[duration]])
#    predicted_time = model.predict(duration_scaled)
#    return 1.05 * int(predicted_time[0])

def round_to_10(number):
    return round(number / 10) * 10


def predict_downloading_time(duration):
    time = int(0.03 * duration + 10)
    return round_to_10(time)

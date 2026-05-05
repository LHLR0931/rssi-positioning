import json
import math
import random
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from api.models import ResponseModel, EmailVerificationTokens, WiFiData
from api.serializer import UserSerializer, WifiDataSerializer, DistinctXYSerializer
from backend.settings import EMAIL_HOST_USER
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Avg
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import LabelEncoder

from .deeplearning.CNNTrain import predict
from .deeplearning.finger_data_process import get_fingerprint, create_prediction_vector
from .deeplearning.GNNTrain import predict as gnn_Predict


def _resolve_latest_checkpoint(checkpoint_dir: Path, label: str) -> Path:
    checkpoints = sorted(
        checkpoint_dir.glob("last*.ckpt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not checkpoints:
        raise FileNotFoundError(f"No {label} checkpoints found in {checkpoint_dir}")
    return checkpoints[0]


def resolve_latest_cnn_checkpoint() -> Path:
    project_root = Path(__file__).resolve().parents[1]
    return _resolve_latest_checkpoint(project_root / "cnn_checkpoints", "CNN")


def resolve_latest_gnn_checkpoint() -> Path:
    project_root = Path(__file__).resolve().parents[1]
    return _resolve_latest_checkpoint(project_root / "gnn_checkpoints", "GNN")





def is_valid_email(email):
    # Regular expression for a valid email address
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

    # Use the re.match() function to check if the email matches the pattern
    if re.match(pattern, email):
        return True
    else:
        return False
    
class WifiDataImport(APIView):
    def post(self, request):
        try:
            # Get the uploaded JSON file from the request
            wifi_data_file = request.FILES['wifiDataFile']
            
            # Parse the JSON file
            wifi_data_list = JSONParser().parse(wifi_data_file)

            # Validate and save the data to the database
            # (You might need to adjust this part based on your data model and serializer)
            serializer = WifiDataSerializer(data=wifi_data_list, many=True)
            if serializer.is_valid():
                serializer.save()
                return Response(ResponseModel.success("", "WiFi Data imported successfully"))
            else:
                return Response(ResponseModel.error(serializer.errors, code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(ResponseModel.error(str(e), code=status.HTTP_500_INTERNAL_SERVER_ERROR), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WifiDataExport(APIView):
    def get(self, request):
        try:
            # Get all WiFi data from the database
            wifi_data = WiFiData.objects.all()

            # Serialize the data
            serializer = WifiDataSerializer(wifi_data, many=True)

            # Convert the serialized data to JSON
            wifi_data_json = json.dumps(serializer.data, indent=2)

            # Save the JSON data to a file
            export_file_path = 'wifi_data_export.json'
            with open(export_file_path, 'w') as file:
                file.write(wifi_data_json)

            # Return the exported file as a response with appropriate headers
            response = FileResponse(open(export_file_path, 'rb'))
            response['Content-Disposition'] = 'attachment; filename="wifi_data_export.json"'
            return response

        except Exception as e:
            return Response(ResponseModel.error(str(e), code=status.HTTP_500_INTERNAL_SERVER_ERROR), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserLogin(APIView):
    def post(self, request):
        username = request.data.get('email')
        password = request.data.get('password')
        if username is None or password is None:
            return Response(ResponseModel.error("email and password is required.",code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)
        user = get_object_or_404(User, username=username)
        if not user.is_active :
            return Response(ResponseModel.error("Account is not active, please check your email to activate your account",code=status.HTTP_403_FORBIDDEN), status=status.HTTP_403_FORBIDDEN)
        if not user.check_password(request.data['password']):
            return Response(ResponseModel.error("User or password is wrong",code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)
        token, created = Token.objects.get_or_create(user=user)
        serializer= UserSerializer(instance=user)
        return Response(ResponseModel.success({"token" : token.key, "user":serializer.data }, "Log in success"))

@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
class UsersList(APIView):
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(ResponseModel.success(serializer.data, ""))

class UserSignup(APIView):
    def post(self, request):
        username = request.data.get('email')
        password = request.data.get('password')
        if username is None or password is None:
            return Response(ResponseModel.error("email and password is required.",code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)
        if (not is_valid_email(username)):
            return Response(ResponseModel.error("Email is not valid.",code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)
        request.data['username']=username;
        request.data['is_active']="false";

        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            user=User.objects.get(username = username)
            user.set_password(password)
            user.save()
            token = Token.objects.create(user=user)
            # for email verification code, i saved it in token field in emailverificationtokens table
            expired_date = datetime.now() + timedelta(days=1)  # Adjust as needed
            email_token = EmailVerificationTokens(
            token=verification_code,
            user_id=user.id,
            expired_date=expired_date,
            )
            email_token.save()
            context = {
                'verification_code': verification_code,
            }

            # render email text
            email_html_message = render_to_string('activate_account_email.html', context)

            subject = 'Account Activation'
            message = ""
            from_email = EMAIL_HOST_USER
            recipient_list = [user.email]

            send_mail(subject, message, from_email, recipient_list,
            fail_silently=False,
            html_message=email_html_message)
            return Response(ResponseModel.success({"token" : token.key, "user":serializer.data }, "Sign up success, please check your email to activate your account"))
        else:
            return Response(ResponseModel.error(serializer.errors,code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)


class ResendEmailVerification(APIView):
    def post(self, request):
        username = request.data.get('email')
        if username is None :
            return Response(ResponseModel.error("email is required.",code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)
        if (not is_valid_email(username)):
            return Response(ResponseModel.error("Email is not valid.",code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)

        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        user=User.objects.get(username = username)
        if user.is_active :
            return Response(ResponseModel.error("Account is already active",code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)

        # for email verification code, i saved it in token field in emailverificationtokens table
        expired_date = datetime.now() + timedelta(days=1)  # Adjust as needed
        email_token = EmailVerificationTokens(
        token=verification_code,
        user_id=user.id,
        expired_date=expired_date,
        )
        email_token.save()
        context = {
            'verification_code': verification_code,
        }

        # render email text
        email_html_message = render_to_string('activate_account_email.html', context)

        subject = 'Account Activation'
        message = ""
        from_email = EMAIL_HOST_USER
        recipient_list = [user.email]

        send_mail(subject, message, from_email, recipient_list,
        fail_silently=False,
        html_message=email_html_message)
        return Response(ResponseModel.success("", "Resend Email Verification success, please check your email to activate your account"))

class CheckEmailVerification(APIView):
    def post(self, request):
        email = request.data.get('email')
        verification_code = request.data.get('verification_code')
        if email is None or verification_code is None:
            return Response(ResponseModel.error("email and verification_code is required.",code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)
        user = get_object_or_404(User, username=email)
        if user.is_active :
            return Response(ResponseModel.error("Account is already active",code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)

        emailVerification = EmailVerificationTokens.objects.filter(user_id=user.id, is_active=True).latest('last_created_date')
        # print (emailVerification.token)
        # if emailVerification.expired_date < timezone.now():
        #     return Response(ResponseModel.error("Verification email has expired.", code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)

        if verification_code==emailVerification.token:
            user.is_active=True
            user.save()
            emailVerification.is_active = False  # Deactivate the used email verification
            emailVerification.save()
            return Response(ResponseModel.success("", "Verification email success"))
        else:
            return Response(ResponseModel.error("Verification email failed", code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)

class WiFiDataListXY(APIView):
    def get(self, request):
        # Use values to select only 'x' and 'y' fields and then apply distinct
        wifi_datas = WiFiData.objects.values('x', 'y').distinct()
        
        # You can serialize the data if needed
        serializer = DistinctXYSerializer(wifi_datas, many=True)
        return Response(ResponseModel.success(serializer.data, ""))
    
# @authentication_classes([SessionAuthentication, TokenAuthentication])
# @permission_classes([IsAuthenticated])
class WiFiDataList(APIView):
    def get(self, request):
        wifiDatas = WiFiData.objects.all()
        serializer = WifiDataSerializer(wifiDatas, many=True)
        return Response(ResponseModel.success(serializer.data, ""))
    def post(self, request):
        wifi_data_list = request.data.get('wifiData', [])
        x = request.data.get('x', request.data.get('X'))
        y = request.data.get('y', request.data.get('Y'))
        data_type = request.data.get('data_type', request.data.get('dataType'))
        wifi_data_objects = []

        if x is None or y is None:
            return Response(
                ResponseModel.error(
                    "Missing required coordinates. Send x and y at the JSON root, for example: "
                    '{"x": 0, "y": 1, "wifiData": [...]}',
                    code=status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            x = float(x)
            y = float(y)
            if data_type is not None:
                data_type = float(data_type)
        except (TypeError, ValueError):
            return Response(
                ResponseModel.error("Coordinates x/y and data_type must be numbers.", code=status.HTTP_400_BAD_REQUEST),
                status=status.HTTP_400_BAD_REQUEST
            )

        for wifi_data_item in wifi_data_list:
            wifi_data_item['x'] = x
            wifi_data_item['y'] = y
            if data_type is not None:
                wifi_data_item['data_type'] = data_type
            serializer = WifiDataSerializer(data=wifi_data_item)
            if serializer.is_valid():
                wifi_data_objects.append(WiFiData(**serializer.validated_data))
            else:
                return Response(
                    ResponseModel.error(serializer.errors, code=status.HTTP_400_BAD_REQUEST),
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 使用 bulk_create 来一次性插入数据
        with transaction.atomic():
            WiFiData.objects.bulk_create(wifi_data_objects)

        return Response(ResponseModel.success({
            "saved_count": len(wifi_data_objects),
            "x": x,
            "y": y,
            "data_type": data_type,
            "items": WifiDataSerializer(wifi_data_objects, many=True).data
        }, ""))
    
# @authentication_classes([SessionAuthentication, TokenAuthentication])
# @permission_classes([IsAuthenticated])
class WifiDataDetail(APIView):
    def get_object(self, pk):
        try:
            return WiFiData.objects.get(pk=pk)
        except ValidationError as e:
            return Response(ResponseModel.error(e,code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)
        except WiFiData.DoesNotExist:
            return Response(ResponseModel.error("Wifi Data does not exist",code=status.HTTP_404_NOT_FOUND), status=status.HTTP_404_NOT_FOUND)

    def get(self, request, pk):
        wifiData = self.get_object(pk)
        if isinstance(wifiData, Response):
            return wifiData;
        serializer = WifiDataSerializer(wifiData)
        return Response(ResponseModel.success(serializer.data, ""))

    def put(self, request, pk):
        wifiData = self.get_object(pk)
        if isinstance(wifiData, Response):
            return wifiData;
        serializer = WifiDataSerializer(wifiData, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(ResponseModel.success(serializer.data, ""))
        return Response(ResponseModel.error(serializer.errors,code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        wifiData = self.get_object(pk)
        if isinstance(wifiData, Response):
            return wifiData;
        wifiData.delete()
        return Response(ResponseModel.success("", "WiFi Data deleted"))
    

class WifiDataDelete(APIView):
    def get_objects(self, x, y):
        try:
            return WiFiData.objects.filter(x=x, y=y)
        except ValidationError as e:
            return Response(ResponseModel.error(e, code=status.HTTP_400_BAD_REQUEST), status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        x = request.data.get('x')
        y = request.data.get('y')
        wifi_data_instances = self.get_objects(x, y)
        
        # Delete all instances
        wifi_data_instances.delete()

        return Response(ResponseModel.success("", "WiFi Data deleted"))
    
# Train + Predict

def euclidean_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)


def get_request_coordinate(request, lower_name, upper_name):
    value = request.data.get(lower_name, request.data.get(upper_name))
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_prediction_payload(prediction_key, predict_position, actual_x=None, actual_y=None):
    data = {
        "x": predict_position["x"],
        "y": predict_position["y"],
        prediction_key: predict_position,
    }

    if actual_x is not None and actual_y is not None:
        error_meters = euclidean_distance(actual_x, actual_y, predict_position["x"], predict_position["y"])
        actual_position = {"x": actual_x, "y": actual_y}
        data.update({
            "actual_x": actual_x,
            "actual_y": actual_y,
            "actual_position": actual_position,
            "predicted_x": predict_position["x"],
            "predicted_y": predict_position["y"],
            "predicted_position": predict_position,
            "error": error_meters,
            "error_meters": error_meters,
            "distance": error_meters,
            "distance_meters": error_meters,
            "line": {
                "from": actual_position,
                "to": predict_position,
            },
        })

    return data

class WifiTrainPredictPosition(APIView):
    def post(self, request):
        # Get input Wi-Fi data from the request
        wifi_data_list = request.data.get('wifiData', [])
        actual_x = get_request_coordinate(request, "x", "X")
        actual_y = get_request_coordinate(request, "y", "Y")

        if not wifi_data_list:
            return JsonResponse({'error': 'Empty list of WiFi data points'})

        # Dictionary to store accumulated RSSI values, count, and ssid for each BSSID
        bssid_data = defaultdict(lambda: {"sum_rssi": 0, "count": 0, "ssid": set()})

        # Process each WiFi data entry
        for entry in wifi_data_list:
            bssid = entry["bssid"]
            rssi = entry["rssi"]
            ssid = entry["ssid"]

            # Filter out entries with RSSI 0 or more less -75
            if -75 < rssi < 0:
                # Accumulate RSSI values, increment count, and store ssid for each BSSID
                bssid_data[bssid]["sum_rssi"] += rssi
                bssid_data[bssid]["count"] += 1
                bssid_data[bssid]["ssid"].add(ssid)

        # Create a new list to store the averaged data
        averaged_wifi_data = []

        # Generate the averaged data for each BSSID
        for bssid, data in bssid_data.items():
            averaged_rssi = data["sum_rssi"] / data["count"]
            ssid = list(data["ssid"])[0]  # Assuming all ssids are the same for a given bssid
            averaged_wifi_data.append({"bssid": bssid, "rssi": averaged_rssi, "ssid": ssid})


        # Encode categorical features using LabelEncoder
        ssid_encoder = LabelEncoder()
        bssid_encoder = LabelEncoder()

        ssid_encoded = ssid_encoder.fit_transform([item['ssid'] for item in averaged_wifi_data])
        bssid_encoded = bssid_encoder.fit_transform([item['bssid'] for item in averaged_wifi_data])
        rssi_values = [int(item['rssi']) for item in averaged_wifi_data]

        # Prepare data for prediction
        X_pred = list(zip(ssid_encoded, bssid_encoded, rssi_values))
        # print (X_pred)
        # Load trained models from the database or a file

        # Train KNN model
        # No need to average
        # survey_data = WiFiData.objects.values('ssid', 'bssid', 'rssi', 'x', 'y')
        survey_data = WiFiData.objects.values('ssid', 'bssid', 'x', 'y').annotate(rssi=Avg('rssi')) 
        # Convert the queryset to a list of dictionaries
        survey_data_list = list(survey_data)

        # Prepare data for training
        X = [[item['ssid'], item['bssid'], item['rssi']] for item in survey_data_list]
        y = [[item['x'], item['y']] for item in survey_data_list]

        # Convert lists to DataFrame
        df = pd.DataFrame(X, columns=['ssid', 'bssid', 'rssi'])
        
        df['x'] = [item[0] for item in y]
        df['y'] = [item[1] for item in y]

        # Encode categorical variables
        label_encoder_ssid = LabelEncoder()
        label_encoder_bssid = LabelEncoder()

        df['ssid'] = label_encoder_ssid.fit_transform(df['ssid'])
        df['bssid'] = label_encoder_bssid.fit_transform(df['bssid'])

        # Split data into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(df[['ssid', 'bssid', 'rssi']], df[['x', 'y']], test_size=0.2, random_state=42)

        # Train KNN model with GridSearchCV
        param_grid = {
            'n_neighbors': range(1, 50),
            'weights': ['uniform', 'distance']
        }

        knn_model = KNeighborsRegressor()
        grid_search = GridSearchCV(knn_model, param_grid, cv=5, scoring='neg_mean_squared_error')
        grid_search.fit(X_train, y_train)

        best_knn_model = grid_search.best_estimator_

        # Simple Train KNN model
        # knn_model = KNeighborsRegressor(n_neighbors=3)
        # knn_model.fit(X_train, y_train)

        # Train Random Forest model
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        rf_model.fit(X_train, y_train)

        # Make predictions using the trained models
        # print("pred : ");
        # print(X_pred);
        knn_predictions = best_knn_model.predict(X_pred)
        # knn_predictions = knn_model.predict(X_pred)
        rf_predictions = rf_model.predict(X_pred)

        # Extract the first result of each knn and rf prediction
        knn_first_result = {'x': knn_predictions[0][0], 'y': knn_predictions[0][1]}
        rf_first_result = {'x': rf_predictions[0][0], 'y': rf_predictions[0][1]}

        # Return predictions as JSON
        knn_average = {
            'x': sum(prediction[0] for prediction in knn_predictions) / len(knn_predictions),
            'y': sum(prediction[1] for prediction in knn_predictions) / len(knn_predictions),
        }

        rf_average= {
            'x': sum(prediction[0] for prediction in rf_predictions) / len(rf_predictions),
            'y': sum(prediction[1] for prediction in rf_predictions) / len(rf_predictions),
        }

        knn_results = [{'x': pred[0], 'y': pred[1]} for pred in knn_predictions]
        rf_results = [{'x': pred[0], 'y': pred[1]} for pred in rf_predictions]

        # Calculate the Euclidean distance for each prediction
        knn_distances = [euclidean_distance(knn_first_result['x'], knn_first_result['y'], pred[0], pred[1]) for pred in knn_predictions]
        rf_distances = [euclidean_distance(rf_first_result['x'], rf_first_result['y'], pred[0], pred[1]) for pred in rf_predictions]

        # Find the index of the prediction with the minimum distance
        closest_knn_index = knn_distances.index(min(knn_distances))
        closest_rf_index = rf_distances.index(min(rf_distances))

        # Get the closest prediction
        closest_knn_result = {'x': knn_predictions[closest_knn_index][0], 'y': knn_predictions[closest_knn_index][1]}
        closest_rf_result = {'x': rf_predictions[closest_rf_index][0], 'y': rf_predictions[closest_rf_index][1]}


        data = build_prediction_payload("knn_first_result", knn_first_result, actual_x, actual_y)
        data.update({
            'x': closest_knn_result['x'],
            'y': closest_knn_result['y'],
            'knn_predictions': knn_results,
            'rf_predictions': rf_results,
            'knn_average': knn_average,
            'rf_average': rf_average,
            'knn_first_result': knn_first_result,
            'rf_first_result': rf_first_result,
            'closest_knn_result': closest_knn_result,
            'closest_rf_result': closest_rf_result
        })
        return Response(ResponseModel.success(data, "Predict success"))


def get_avg_rssi(request):
    wifi_data_list = request.data.get('wifiData', [])
    if not wifi_data_list:
        return None

    bssid_data = defaultdict(lambda: {"sum_rssi": 0, "count": 0, "ssid": None})

    for entry in wifi_data_list:
        bssid = entry["bssid"].lower().strip()
        rssi = entry["rssi"]
        ssid = entry["ssid"]

        if bssid_data[bssid]["ssid"] is None:
            bssid_data[bssid]["ssid"] = ssid

        bssid_data[bssid]["sum_rssi"] += rssi
        bssid_data[bssid]["count"] += 1

    averaged_wifi_data = []
    for bssid, data in bssid_data.items():
        averaged_rssi = data["sum_rssi"] / data["count"]
        averaged_wifi_data.append({"bssid": bssid, "rssi": averaged_rssi, "ssid": data["ssid"]})

    return averaged_wifi_data


# new method for fingerprinting    
class WifiFingerprintingTrainPredictPosition(APIView):
    def post(self, request):
        # Get input Wi-Fi data from the request
        averaged_wifi_data = get_avg_rssi(request)
        if not averaged_wifi_data:
            return JsonResponse({'error': 'Empty list of WiFi data points'})

        actual_x = get_request_coordinate(request, "x", "X")
        actual_y = get_request_coordinate(request, "y", "Y")

      # Convert fingerprint vector to DataFrame
      # fromDB = False to get data from JSON file, True to get data from the database
        df,unique_bssids =  get_fingerprint(data_type=0)

        # split dataset
        X = df.drop(['x', 'y'], axis=1)
        y = df[['x', 'y']]
        # X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        X_train = X
        y_train = y

        # Train the KNN model
        knn_param_grid = {'n_neighbors': range(3, 15), 'weights': ['uniform', 'distance']}
        knn_grid_search = GridSearchCV(KNeighborsRegressor(), knn_param_grid, cv=5, scoring='neg_mean_squared_error')
        knn_grid_search.fit(X_train, y_train)

        # Train a random forest model
        rf_param_grid = {'n_estimators': [5, 10, 20], 'max_features': ['auto', 'sqrt', 'log2']}
        rf_grid_search = GridSearchCV(RandomForestRegressor(random_state=42), rf_param_grid, cv=5, scoring='neg_mean_squared_error')
        rf_grid_search.fit(X_train, y_train)

        # Outputs the parameters of the best model
        best_knn_params = knn_grid_search.best_params_
        best_rf_params = rf_grid_search.best_params_


        #  Create a prediction vector
        X_pred = create_prediction_vector(averaged_wifi_data, unique_bssids)
      
        knn_predictions = knn_grid_search.predict(X_pred)
        rf_predictions = rf_grid_search.predict(X_pred)

        knn_position = {'x':knn_predictions.tolist()[0][0], 'y':knn_predictions.tolist()[0][1]} 
        rf_position = {'x':rf_predictions.tolist()[0][0], 'y':rf_predictions.tolist()[0][1]}

        data = build_prediction_payload("finger_knn_predictions", knn_position, actual_x, actual_y)
        data.update({
            'x': knn_position['x'],
            'y': knn_position['y'],
            # 'KNN Best Params': best_knn_params,
            # 'Random Forest Best Params': best_rf_params,
            'finger_knn_predictions':knn_position, 
            'finger_rf_predictions': rf_position,   
        })
        return JsonResponse(ResponseModel.success(data))
    
# cnn method
class WifiCNNPredictPosition(APIView):
    def post(self, request):
        averaged_wifi_data = get_avg_rssi(request)
        if not averaged_wifi_data:
            return JsonResponse({'error': 'Empty list of WiFi data points'})

        actual_x = get_request_coordinate(request, "x", "X")
        actual_y = get_request_coordinate(request, "y", "Y")

        df_fp, unique_bssids = get_fingerprint(data_type=0)
        unique_bssids = [b.lower().strip() for b in unique_bssids]

        X_pred = create_prediction_vector(averaged_wifi_data, unique_bssids)


        # 确保传给 predict 的是 DataFrame，列顺序与 unique_bssids 对齐
        if isinstance(X_pred, pd.DataFrame):
            pass  # 已经是 DF，保持不动
        elif isinstance(X_pred, np.ndarray):
            X_pred = pd.DataFrame(X_pred.reshape(1, -1), columns=unique_bssids)
        elif isinstance(X_pred, (list, tuple)):
            X_pred = pd.DataFrame([X_pred], columns=unique_bssids)
        else:
        # 最兜底：直接强转
            X_pred = pd.DataFrame(np.asarray(X_pred).reshape(1, -1), columns=unique_bssids)

        #print("DBG X_TYPE =", type(X_pred), "X_SHAPE =", getattr(X_pred, "shape", None), "HAS_to_numpy", hasattr(X_pred, "to_numpy"))



        #print("DBG X_SHAPE (should be 1 x FP_LEN) =", X_pred.shape)


        try:
            model_path = resolve_latest_cnn_checkpoint()
        except FileNotFoundError as e:
            return JsonResponse(
                ResponseModel.error(str(e), code=status.HTTP_500_INTERNAL_SERVER_ERROR),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        print("DBG CNN MODEL_PATH =", model_path, "EXISTS?", model_path.exists())

        predictions = predict(str(model_path), X_pred)
        # —— 打印模型原始输出 —— #
        #print("DBG PRED_RAW type:", type(predictions), "shape:", getattr(predictions, "shape", None))
        try:
            # 列表/数组/张量都转成一维
            arr = np.asarray(predictions, dtype=float).reshape(-1)
        except Exception as e:
            print("DBG PRED toarray ERR:", e)
            arr = np.array([])

        #print("DBG ARR:", arr, "SIZE:", arr.size, "ISFINITE:", np.isfinite(arr).all())

        # —— 安全取 x,y（兜底防止空/NaN） —— #
        x = float(arr[0]) if arr.size > 0 and np.isfinite(arr[0]) else 0.0
        y = float(arr[1]) if arr.size > 1 and np.isfinite(arr[1]) else 0.0
        #print(f"DBG RETURN x={x}, y={y}")

        predict_position = {"x": x, "y": y}
        return JsonResponse(ResponseModel.success(
            build_prediction_payload("cnn_predictions", predict_position, actual_x, actual_y)
        ))

        #arr = np.asarray(predictions, dtype=float).reshape(-1)
        #predict_position = {"x": float(arr[0]), "y": float(arr[1])}
        #return JsonResponse(ResponseModel.success({"cnn_predictions": predict_position}))
        
# gnn method
class WifiGNNPredictPosition(APIView):
    def post(self, request):
        # Get input Wi-Fi data from the request
        averaged_wifi_data = get_avg_rssi(request)
        if not averaged_wifi_data:
            return JsonResponse({'error': 'Empty list of WiFi data points'})

        actual_x = get_request_coordinate(request, "x", "X")
        actual_y = get_request_coordinate(request, "y", "Y")

        project_root = Path(__file__).resolve().parents[1]
        db_path = project_root / 'db_new.sqlite3'
        try:
            model_path = resolve_latest_gnn_checkpoint()
        except FileNotFoundError as e:
            return JsonResponse(
                ResponseModel.error(str(e), code=status.HTTP_500_INTERNAL_SERVER_ERROR),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
       
        predictions = gnn_Predict(str(model_path), averaged_wifi_data, db_path=str(db_path))
      
        predict_position = {'x':predictions.tolist()[0][0], 'y':predictions.tolist()[0][1]}

        data = build_prediction_payload("gnn_predictions", predict_position, actual_x, actual_y)
        data.update({
            'x': predict_position['x'],
            'y': predict_position['y'],
            'gnn_predictions': predict_position
        })
        return JsonResponse(ResponseModel.success(data))


class WifiDataSplit(APIView):
    """
    POST /api/wifidata/splitdata/
    Randomly redistribute all WiFiData into train/val/test at 6:2:2,
    splitting within each (x, y) location so every point has training samples.
    """
    def post(self, request):
        all_items = list(WiFiData.objects.values('wifi_data_id', 'x', 'y'))
        if not all_items:
            return Response(
                ResponseModel.error("No WiFi data found.", code=status.HTTP_400_BAD_REQUEST),
                status=status.HTTP_400_BAD_REQUEST,
            )

        by_location = defaultdict(list)
        for item in all_items:
            by_location[(item['x'], item['y'])].append(item['wifi_data_id'])

        train_ids, val_ids, test_ids = [], [], []
        for loc_ids in by_location.values():
            random.shuffle(loc_ids)
            n = len(loc_ids)
            n_train = max(1, round(n * 0.6))
            n_val = max(0, round(n * 0.2))
            train_ids.extend(loc_ids[:n_train])
            val_ids.extend(loc_ids[n_train:n_train + n_val])
            test_ids.extend(loc_ids[n_train + n_val:])

        with transaction.atomic():
            WiFiData.objects.filter(wifi_data_id__in=train_ids).update(data_type=0)
            WiFiData.objects.filter(wifi_data_id__in=val_ids).update(data_type=1)
            WiFiData.objects.filter(wifi_data_id__in=test_ids).update(data_type=2)

        total = len(all_items)
        return Response(ResponseModel.success(
            {
                "total": total,
                "train": len(train_ids),
                "val": len(val_ids),
                "test": len(test_ids),
                "ratio": f"{len(train_ids)/total*100:.0f}% / {len(val_ids)/total*100:.0f}% / {len(test_ids)/total*100:.0f}%",
            },
            "Data split 6:2:2 by location successfully.",
        ))
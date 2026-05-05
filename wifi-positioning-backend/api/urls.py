from django.urls import path, include
from api.views import (
    WiFiDataListXY, WifiDataImport, WifiDataExport, WifiDataDelete,
    WifiTrainPredictPosition, WifiCNNPredictPosition,
    WifiFingerprintingTrainPredictPosition, WifiGNNPredictPosition,
    UserLogin, UsersList, UserSignup, ResendEmailVerification,
    CheckEmailVerification, WifiDataDetail, WiFiDataList, WifiDataSplit,
)

urlpatterns = [
    path('users/resetpassword/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    path('signup/', UserSignup.as_view()),
    path('login/', UserLogin.as_view()),
    path('users/', UsersList.as_view()),
    path('users/resendemailverification/', ResendEmailVerification.as_view()),
    path('users/emailverification/', CheckEmailVerification.as_view()),
    path('wifidata/survey_xy/', WiFiDataListXY.as_view()),
    path('wifidata/', WiFiDataList.as_view()),
    path('wifidata/bycoor/', WifiDataDelete.as_view()),
    path('wifidata/<uuid:pk>/', WifiDataDetail.as_view()),
    path('wifidata/export/', WifiDataExport.as_view()),
    path('wifidata/import/', WifiDataImport.as_view()),
    path('wifidata/predict/', WifiTrainPredictPosition.as_view()),
    path('wifidata/fingerprinting/', WifiFingerprintingTrainPredictPosition.as_view()),
    path('wifidata/cnnpredict/', WifiCNNPredictPosition.as_view()),
    path('wifidata/gnnpredict/', WifiGNNPredictPosition.as_view()),
    path('wifidata/splitdata/', WifiDataSplit.as_view()),
]

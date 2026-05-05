package com.example.vri.utils;

import com.example.vri.models.ApiResponseModel;
import com.example.vri.models.PredictionModel;
import com.example.vri.models.WifiDataDTOModel;
import okhttp3.ResponseBody;
import java.util.List;
import java.util.Map;

import retrofit2.Call;
import retrofit2.http.*;

public interface APIHelper {
    @GET("wifidata/")
    Call<ApiResponseModel<Object>> getAllWifiDatas();
    @GET("wifidata/survey_xy/")
    Call<ApiResponseModel<Object>> getAllSurveyDatas();
    @POST("wifidata/")
    Call<ApiResponseModel<Object>> saveWifiData(@Body WifiDataDTOModel post);

    @POST("wifidata/predict/")
    Call<ApiResponseModel<PredictionModel>> predictPosition(@Body WifiDataDTOModel post);

    @POST("wifidata/fingerprinting/")
    Call<ApiResponseModel<PredictionModel>> fingerPredictPosition(@Body WifiDataDTOModel post);

    @POST("wifidata/cnnpredict/")
    Call<ApiResponseModel<PredictionModel>> cnnPredictPosition(@Body WifiDataDTOModel post);

    @POST("wifidata/gnnpredict/")
    Call<ApiResponseModel<PredictionModel>> gnnPredictPosition(@Body WifiDataDTOModel post);

    @POST("wifidata/splitdata/")
    Call<ApiResponseModel<Object>> splitWifiData();

    @GET("wifidata/export/")
    @Streaming
    Call<ResponseBody> exportWifiData();

    @GET("posts")
    Call<List<WifiDataDTOModel>> getPosts(
            @Query("userId") Integer[] userId,
            @Query("_sort") String sort,
            @Query("_order") String order
    );

    @GET("posts")
    Call<List<WifiDataDTOModel>> getPosts(@QueryMap Map<String, String> parameters);

    @GET("posts/{id}/comments")
    Call<List<WifiDataDTOModel>> getComments(@Path("id") int postId);

    @GET
    Call<List<WifiDataDTOModel>> getComments(@Url String url);
}

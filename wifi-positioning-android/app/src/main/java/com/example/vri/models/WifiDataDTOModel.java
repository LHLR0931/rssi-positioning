package com.example.vri.models;

import com.google.gson.annotations.SerializedName;

import java.util.List;

public class WifiDataDTOModel {
    @SerializedName("x")
    private double x;
    @SerializedName("y")
    private double y;
    @SerializedName("wifiData")
    private List<WifiDataModel> wifiData;

    public WifiDataDTOModel(double x, double y, List<WifiDataModel> wifiData) {
        this.x = x;
        this.y = y;
        this.wifiData = wifiData;
    }

    public double getX() {
        return x;
    }

    public void setX(double x) {
        this.x = x;
    }

    public double getY() {
        return y;
    }

    public void setY(double y) {
        this.y = y;
    }

    public List<WifiDataModel> getWifiData() {
        return wifiData;
    }

    public void setWifiData(List<WifiDataModel> wifiData) {
        this.wifiData = wifiData;
    }

}

package com.example.vri.models;

import com.google.gson.annotations.SerializedName;

public class WifiDataModel {
    @SerializedName("ssid")
    private String ssid;
    @SerializedName("bssid")
    private String bssid;
    @SerializedName("rssi")

    private int rssi;

    @SerializedName("data_type")
    // data type 0 = training, 1 = validation, 2 = test
    private int dataType;
    public WifiDataModel(String ssid, String bssid, int rssi, int dataType) {
        this.ssid = ssid;
        this.bssid = bssid;
        this.rssi = rssi;
        this.dataType = dataType;
    }

    public WifiDataModel(String ssid, String bssid, int rssi) {
        this.ssid = ssid;
        this.bssid = bssid;
        this.rssi = rssi;
    }



    public String getSsid() {
        return ssid;
    }

    public void setSsid(String ssid) {
        this.ssid = ssid;
    }

    public String getBssid() {
        return bssid;
    }

    public void setBssid(String bssid) {
        this.bssid = bssid;
    }

    public int getRssi() {
        return rssi;
    }

    public void setRssi(int rssi) {
        this.rssi = rssi;
    }

    public int getDataType() {
        return dataType;
    }

    public void setDataType(int dataType) {
        this.dataType = dataType;
    }
}

package com.example.vri.models;

import java.util.List;

public class PredictionModel {
    private List<PointModel> knn_predictions;
    private List<PointModel> rf_predictions;
    private PointModel knn_average;
    private PointModel rf_average;
    private PointModel knn_first_result;
    private PointModel rf_first_result;
    private PointModel closest_knn_result;
    private PointModel closest_rf_result;

    private PointModel gnn_predictions;


    private PointModel finger_knn_predictions;
    private PointModel finger_rf_predictions;

    private PointModel cnn_predictions;

    private double error_meters;
    private double actual_x;
    private double actual_y;

    public double getError_meters() { return error_meters; }
    public void setError_meters(double error_meters) { this.error_meters = error_meters; }
    public double getActual_x() { return actual_x; }
    public void setActual_x(double actual_x) { this.actual_x = actual_x; }
    public double getActual_y() { return actual_y; }
    public void setActual_y(double actual_y) { this.actual_y = actual_y; }

    public PointModel getClosest_knn_result() {
        return closest_knn_result;
    }

    public void setClosest_knn_result(PointModel closest_knn_result) {
        this.closest_knn_result = closest_knn_result;
    }

    public PointModel getClosest_rf_result() {
        return closest_rf_result;
    }

    public void setClosest_rf_result(PointModel closest_rf_result) {
        this.closest_rf_result = closest_rf_result;
    }

    public PointModel getKnn_average() {
        return knn_average;
    }

    public void setKnn_average(PointModel knn_average) {
        this.knn_average = knn_average;
    }

    public PointModel getRf_average() {
        return rf_average;
    }

    public void setRf_average(PointModel rf_average) {
        this.rf_average = rf_average;
    }

    public PointModel getKnn_first_result() {
        return knn_first_result;
    }

    public void setKnn_first_result(PointModel knn_first_result) {
        this.knn_first_result = knn_first_result;
    }

    public PointModel getRf_first_result() {
        return rf_first_result;
    }

    public void setRf_first_result(PointModel rf_first_result) {
        this.rf_first_result = rf_first_result;
    }

    public List<PointModel> getKnn_predictions() {
        return knn_predictions;
    }

    public void setKnn_predictions(List<PointModel> knn_predictions) {
        this.knn_predictions = knn_predictions;
    }

    public List<PointModel> getRf_predictions() {
        return rf_predictions;
    }

    public void setRf_predictions(List<PointModel> rf_predictions) {
        this.rf_predictions = rf_predictions;
    }

    public PointModel getCnn_predictions() {
        return cnn_predictions;
    }

    public void setCnn_predictions(PointModel cnn_predictions) {
        this.cnn_predictions = cnn_predictions;
    }

    public PointModel getFinger_knn_predictions() {
        return finger_knn_predictions;
    }

    public void setFinger_knn_predictions(PointModel finger_knn_predictions) {
        this.finger_knn_predictions = finger_knn_predictions;
    }

    public PointModel getFinger_rf_predictions() {
        return finger_rf_predictions;
    }

    public void setFinger_rf_predictions(PointModel finger_rf_predictions) {
        this.finger_rf_predictions = finger_rf_predictions;
    }

    public PointModel getGnn_predictions() {
        return gnn_predictions;
    }

    public void setGnn_predictions(PointModel gnn_predictions) {
        this.gnn_predictions = gnn_predictions;
    }
}


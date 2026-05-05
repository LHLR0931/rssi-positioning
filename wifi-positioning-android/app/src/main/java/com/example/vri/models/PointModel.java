package com.example.vri.models;

public class PointModel {
    private double x;
    private double y;

    public PointModel() {
    }
    public PointModel(double x, double y) {
        this.x = x;
        this.y = y;
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
}

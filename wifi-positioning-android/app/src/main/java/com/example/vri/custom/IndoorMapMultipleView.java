package com.example.vri.custom;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.util.AttributeSet;
import android.view.View;

import com.example.vri.models.PointModel;

import java.util.ArrayList;
import java.util.List;

public class IndoorMapMultipleView extends View {

    // Dynamic scale — updated when survey points are loaded
    private float xScale = 6f;
    private float yScale = 6f;

    private List<PointModel> coordinates;
    private List<PointModel> specificPoints;
    private PointModel averageCoordinate;
    private PointModel currentPosition;
    private List<PointModel> surveyPoints;
    private List<PointModel> apPoints;

    private Paint surveyPointPaint;
    private Paint apPointPaint;
    private Paint blackPaint;
    private Paint redPaint;
    private Paint bluePaint;
    private Paint currentPositionPaint;
    private Paint specificPointPaint;
    private Paint linePaint;
    private Paint textPaint;
    private Paint coordLabelPaint;
    private Paint backgroundFillPaint;
    private Paint gridAxisPaint;

    private Bitmap backgroundImage;

    public IndoorMapMultipleView(Context context, AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    private void init() {
        backgroundFillPaint = new Paint();
        backgroundFillPaint.setColor(Color.parseColor("#F8F9FA"));
        backgroundFillPaint.setStyle(Paint.Style.FILL);

        linePaint = new Paint();
        linePaint.setColor(Color.parseColor("#00BCD4"));
        linePaint.setStyle(Paint.Style.STROKE);
        linePaint.setStrokeWidth(4);
        linePaint.setAntiAlias(true);

        textPaint = new Paint();
        textPaint.setColor(Color.parseColor("#006064"));
        textPaint.setTextSize(30);
        textPaint.setAntiAlias(true);

        // Label drawn next to each survey point showing (x,y)
        coordLabelPaint = new Paint();
        coordLabelPaint.setColor(Color.parseColor("#BF360C"));
        coordLabelPaint.setTextSize(22);
        coordLabelPaint.setAntiAlias(true);

        surveyPointPaint = new Paint();
        surveyPointPaint.setColor(Color.parseColor("#FFC107"));
        surveyPointPaint.setStyle(Paint.Style.FILL);
        surveyPointPaint.setAntiAlias(true);

        apPointPaint = new Paint();
        apPointPaint.setColor(Color.DKGRAY);
        apPointPaint.setStyle(Paint.Style.FILL);
        apPointPaint.setAntiAlias(true);

        currentPositionPaint = new Paint();
        currentPositionPaint.setColor(Color.parseColor("#E91E63"));
        currentPositionPaint.setStyle(Paint.Style.FILL);
        currentPositionPaint.setAntiAlias(true);

        // Grid lines
        blackPaint = new Paint();
        blackPaint.setColor(Color.parseColor("#CFD8DC"));
        blackPaint.setStyle(Paint.Style.STROKE);
        blackPaint.setStrokeWidth(1);
        blackPaint.setAntiAlias(true);

        // Grid border
        gridAxisPaint = new Paint();
        gridAxisPaint.setColor(Color.parseColor("#546E7A"));
        gridAxisPaint.setStyle(Paint.Style.STROKE);
        gridAxisPaint.setStrokeWidth(2);
        gridAxisPaint.setAntiAlias(true);

        redPaint = new Paint();
        redPaint.setColor(Color.RED);
        redPaint.setStyle(Paint.Style.FILL);
        redPaint.setAntiAlias(true);

        bluePaint = new Paint();
        bluePaint.setColor(Color.BLUE);
        bluePaint.setStyle(Paint.Style.FILL);
        bluePaint.setAntiAlias(true);

        specificPointPaint = new Paint();
        specificPointPaint.setColor(Color.parseColor("#4CAF50"));
        specificPointPaint.setStyle(Paint.Style.FILL);
        specificPointPaint.setAntiAlias(true);

        apPoints = new ArrayList<>();
        surveyPoints = new ArrayList<>();
        coordinates = new ArrayList<>();
        specificPoints = new ArrayList<>();
    }

    public void setBackground(Bitmap background) {
        backgroundImage = background;
        invalidate();
    }

    /**
     * Loads survey points and auto-computes the map scale so all points are visible.
     */
    public void setSurveyPoints(List<PointModel> surveyList) {
        float maxX = 1f, maxY = 1f;
        for (PointModel p : surveyList) {
            maxX = Math.max(maxX, (float) p.getX());
            maxY = Math.max(maxY, (float) p.getY());
        }
        xScale = maxX + 1.5f;
        yScale = maxY + 1.5f;

        surveyPoints.clear();
        surveyPoints.addAll(surveyList);
        invalidate();
    }

    public void setAnchorPoints(List<PointModel> anchorList) {
        apPoints.clear();
        apPoints.addAll(anchorList);
        invalidate();
    }

    public void setCurrentPosition(double x, double y) {
        currentPosition = new PointModel(x, y);
        invalidate();
    }

    public void setCoordinates(List<PointModel> coords) {
        coordinates.clear();
        coordinates.addAll(coords);
        calculateAverageCoordinate();
        invalidate();
    }

    public void addSpecificPoint(double x, double y) {
        specificPoints.add(new PointModel(x, y));
        invalidate();
    }

    public void clearSpecificPoints() {
        specificPoints.clear();
        invalidate();
    }

    private void calculateAverageCoordinate() {
        if (coordinates == null || coordinates.isEmpty()) return;
        float sumX = 0, sumY = 0;
        for (PointModel c : coordinates) { sumX += c.getX(); sumY += c.getY(); }
        averageCoordinate = new PointModel(sumX / coordinates.size(), sumY / coordinates.size());
    }

    // ---- coordinate → canvas pixel helpers ----
    private float toViewX(double coord) { return (float) (coord / xScale * getWidth()); }
    private float toViewY(double coord) { return (float) (coord / yScale * getHeight()); }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        int w = getWidth(), h = getHeight();

        if (backgroundImage != null) {
            canvas.drawBitmap(backgroundImage, 0, 0, null);
        } else {
            canvas.drawRect(0, 0, w, h, backgroundFillPaint);
        }

        canvas.drawRect(0, 0, w, h, gridAxisPaint);
        drawGrid(canvas, w, h);

        // Lines from current position to predicted positions
        if (currentPosition != null && specificPoints != null) {
            for (PointModel sp : specificPoints) {
                canvas.drawLine(
                        toViewX(currentPosition.getX()), toViewY(currentPosition.getY()),
                        toViewX(sp.getX()), toViewY(sp.getY()),
                        linePaint);
            }
        }

        // Survey points (yellow) + coordinate labels
        for (PointModel anchor : surveyPoints) {
            float vx = toViewX(anchor.getX()), vy = toViewY(anchor.getY());
            canvas.drawCircle(vx, vy, 22, surveyPointPaint);
            String label = String.format("(%.0f,%.0f)", anchor.getX(), anchor.getY());
            canvas.drawText(label, vx - coordLabelPaint.measureText(label) / 2f, vy - 28, coordLabelPaint);
        }

        // AP anchor points (dark gray)
        for (PointModel anchor : apPoints) {
            canvas.drawCircle(toViewX(anchor.getX()), toViewY(anchor.getY()), 22, apPointPaint);
        }

        // Current (actual) position — pink
        if (currentPosition != null) {
            float vx = toViewX(currentPosition.getX()), vy = toViewY(currentPosition.getY());
            canvas.drawCircle(vx, vy, 28, currentPositionPaint);
            String label = "You";
            canvas.drawText(label, vx - textPaint.measureText(label) / 2f, vy + 52, textPaint);
        }

        // Extra coordinate list — red
        for (PointModel c : coordinates) {
            canvas.drawCircle(toViewX(c.getX()), toViewY(c.getY()), 16, redPaint);
        }

        // Average — blue
        if (averageCoordinate != null) {
            canvas.drawCircle(toViewX(averageCoordinate.getX()), toViewY(averageCoordinate.getY()), 16, bluePaint);
        }

        // Predicted positions — green
        for (PointModel sp : specificPoints) {
            float vx = toViewX(sp.getX()), vy = toViewY(sp.getY());
            canvas.drawCircle(vx, vy, 28, specificPointPaint);
            String label = "Pred";
            canvas.drawText(label, vx - textPaint.measureText(label) / 2f, vy + 52, textPaint);
        }
    }

    private void drawGrid(Canvas canvas, int w, int h) {
        int nx = Math.round(xScale), ny = Math.round(yScale);
        for (int i = 1; i < ny; i++) {
            float y = (float) i / ny * h;
            canvas.drawLine(0, y, w, y, blackPaint);
        }
        for (int i = 1; i < nx; i++) {
            float x = (float) i / nx * w;
            canvas.drawLine(x, 0, x, h, blackPaint);
        }
    }
}

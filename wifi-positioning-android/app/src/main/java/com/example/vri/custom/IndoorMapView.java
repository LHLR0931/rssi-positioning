package com.example.vri.custom;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.util.AttributeSet;
import android.view.View;

public class IndoorMapView extends View {

    private double xCoordinate; // Replace with your actual x-coordinate
    private double yCoordinate; // Replace with your actual y-coordinate
    private Paint paint;

    public IndoorMapView(Context context, AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    private void init() {
        paint = new Paint();
        paint.setColor(Color.RED);
        paint.setStyle(Paint.Style.FILL);
        paint.setAntiAlias(true);
    }

    public void setCoordinates(double x, double y) {
        // Limit x and y coordinates (adjust these limits as needed)
        xCoordinate = Math.max(0, Math.min(x, 8));
        yCoordinate = Math.max(0, Math.min(y, 12));
        invalidate(); // Trigger a redraw
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);

        // Calculate the position on the view based on x and y coordinates
        float viewX = (float) (xCoordinate / 8 * getWidth()); // Adjust based on the x-coordinate limits
        float viewY = (float) (yCoordinate / 12 * getHeight()); // Adjust based on the y-coordinate limits

        // Draw a point on the canvas
        canvas.drawCircle(viewX, viewY, 10, paint);
    }
}
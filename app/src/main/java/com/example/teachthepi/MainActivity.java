// 2022, Adam Filkor - TeachThePi
package com.example.teachthepi;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;

import android.graphics.Color;
import android.graphics.SurfaceTexture;
import android.graphics.Typeface;
import android.media.MediaCodec;
import android.media.MediaFormat;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.Menu;
import android.view.MenuInflater;
import android.view.MenuItem;
import android.view.Surface;
import android.view.TextureView;
import android.view.View;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;

import com.example.teachthepi.classes.Connection;
import com.example.teachthepi.classes.VideoParams;

import java.nio.ByteBuffer;
import java.util.Arrays;

public class MainActivity extends AppCompatActivity implements TextureView.SurfaceTextureListener {

    private Connection myConn = null;
    private String str = "";
    private TextureView video_surface;
    private  DecoderThread decoderThread;
    private String Pi_address = "192.168.0.117";
    private Button btnA;
    private Button btnB;
    private ProgressBar progress;
    private boolean trainingA = false;
    private boolean trainingB = false;



    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        btnA = (Button) findViewById(R.id.trainingA);
        btnB = (Button) findViewById(R.id.trainingB);
        progress = findViewById(R.id.progressBar);

        // Get a reference to the TextureView in the UI
        video_surface = (TextureView) findViewById(R.id.textureView);

        // Add this class as a call back so we can catch the events from the Surface Texture
        video_surface.setSurfaceTextureListener(this);

        //Perform a networking operation on in main, only with threads
        Thread thread = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    myConn = new Connection(Pi_address, 43334, 3000);
                    if (myConn.isConnected()) {

                        System.out.println("Connected!");
                        myConn.write("..Connected..");
                        setMessage("..Connected to the server..");

                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        });
        thread.start();
    }

    //TODO maybe name it OnState or smth else?
    public void trainingA_Start(View view) {

        if (trainingA == true) {
            //turn off trainingA
            trainingA = false;
            btnA.setText("training_A_start");
            btnA.setBackgroundColor(ContextCompat.getColor(getApplicationContext(), R.color.purple_500));

            //enable the other button
            btnB.setEnabled(true);

            progress.setVisibility(View.INVISIBLE);

            new Thread(new Runnable() {
                @Override
                public void run() {
                    myConn.write("trainingA_Stop");

                    byte[] buffer = new byte[1024];
                    int len = myConn.read(buffer);
                    if (len > 0) {
                        str = new String(buffer, 0, len);
                        str = "Trained " + str + " frames from class A";


                        //Only the original thread that created a view hierarchy can touch its views.
                        new Handler(Looper.getMainLooper()).post(new Runnable(){
                            @Override
                            public void run() {
                                setMessage(str);
                            }
                        });
                    }
                }
            }).start();
        }
        else {
            //start training A
            trainingA = true;
            btnA.setText("Cancel training...");
            btnA.setBackgroundColor(ContextCompat.getColor(getApplicationContext(), R.color.purple_300));

            //disable the other btn
            btnB.setEnabled(false);

            progress.setVisibility(View.VISIBLE);

            new Thread(new Runnable() {
                @Override
                public void run() {

                    myConn.write("trainingA_Start");
                    setMessage("Training A has started...");
                }
            }).start();
        }
    }



    public void trainingB_Start(View view) {

        if (trainingB == true) {
            trainingB = false;
            btnB.setText("training_B_start");
            btnB.setBackgroundColor(ContextCompat.getColor(getApplicationContext(), R.color.purple_500));

            //enable the other button
            btnA.setEnabled(true);

            progress.setVisibility(View.INVISIBLE);

            new Thread(new Runnable() {
                @Override
                public void run() {
                    myConn.write("trainingB_Stop");

                    byte[] buffer = new byte[1024];
                    int len = myConn.read(buffer);
                    if (len > 0) {
                        str = new String(buffer, 0, len);
                        str = "Trained " + str + " frames from class B";


                        //Only the original thread that created a view hierarchy can touch its views.
                        new Handler(Looper.getMainLooper()).post(new Runnable(){
                            @Override
                            public void run() {
                                setMessage(str);
                            }
                        });
                    }
                }
            }).start();
        }
        else {
            //start training B
            trainingB = true;
            btnB.setText("Cancel training...");
            btnB.setBackgroundColor(ContextCompat.getColor(getApplicationContext(), R.color.purple_300));

            //disable the other btn
            btnA.setEnabled(false);

            progress.setVisibility(View.VISIBLE);

            new Thread(new Runnable() {
                @Override
                public void run() {

                    myConn.write("trainingB_Start");
                    setMessage("Training B has started...");
                }
            }).start();
        }
    }

    public void clearTrainingData(final String clearString) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                System.out.println(clearString);
                myConn.write(clearString);

                byte[] buffer = new byte[1024];
                int len = myConn.read(buffer);
                if (len > 0) {
                    str = new String(buffer, 0, len);

                    new Handler(Looper.getMainLooper()).post(new Runnable(){
                        @Override
                        public void run() {
                            setMessage(str);
                        }
                    });
                }
            }
        }).start();
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        MenuInflater inflater = getMenuInflater();
        inflater.inflate(R.menu.my_menu, menu);
        return true;
    }


    @Override
    public boolean onOptionsItemSelected(@NonNull MenuItem item) {
        switch (item.getItemId()) {
            case R.id.del_classA:
                System.out.println("selected del class A");
                clearTrainingData("clearA");
                return true;

            case R.id.del_classB:
                clearTrainingData("clearB");
                return true;

            default:
                return super.onOptionsItemSelected(item);
        }


    }

    @Override
    public void onSurfaceTextureAvailable(@NonNull SurfaceTexture surface, int width, int height) {
        //setMessage("SurfaceTextureAvailable");

        try{
            //start the codec, decode the data coming though the video connection.
            if (myConn.isConnected()) {
                decoderThread = new DecoderThread();
                decoderThread.start();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Override
    public void onSurfaceTextureSizeChanged(@NonNull SurfaceTexture surface, int width, int height) {

    }

    @Override
    public boolean onSurfaceTextureDestroyed(@NonNull SurfaceTexture surface) {
        return false;
    }

    @Override
    public void onSurfaceTextureUpdated(@NonNull SurfaceTexture surface) {

    }

    /**
     * Updates the message textview.
     * @param R_id  An id from the strings.xml file
     */
    private void setMessage(final int R_id) {
        TextView messageView = findViewById(R.id.messageView);
        messageView.setText(R_id);
    }

    /**
     *
     * @param str String, or CharSequence (String is a CharSequence )
     */
    private void setMessage(String str) {
        TextView messageView = findViewById(R.id.messageView);
        messageView.setTypeface(null, Typeface.BOLD);
        messageView.setText(str);
    }


    /**
     * Decoder Thread
     */
    private class DecoderThread extends Thread {
        //local constants
        private final static int BUFFER_SIZE = 16384;
        private final static int NAL_SIZE_INC = 4096;
        private final static int MAX_READ_ERRORS = 300;

        // instance variables
        private MediaCodec m_codec;
        private MediaFormat format;
        private byte[] buffer = null;
        private ByteBuffer[] inputBuffers = null;
        private long presentationTime = System.nanoTime() / 1000;
        private long presentationTimeInc = 66666;
        private int videoPort;
        private Connection videoConnection = null;

        @Override
        public void run() {
            byte[] nal = new byte[NAL_SIZE_INC];
            int nalLen = 0;
            int numZeroes = 0;
            int numReadErrors = 0;
            boolean gotSPS = false;

            try
            {
                // create the m_codec
                m_codec = MediaCodec.createDecoderByType("video/avc");

                // get the video parameters and configure the m_codec
                VideoParams params = myConn.getVideoParams();
                format = MediaFormat.createVideoFormat("video/avc", params.width, params.height);
                format.setInteger(MediaFormat.KEY_FRAME_RATE, params.fps);
                format.setInteger(MediaFormat.KEY_BIT_RATE, params.bps);
                m_codec.configure(format, new Surface(video_surface.getSurfaceTexture()), null, 0);
                //System.out.println(String.format("%d,%d,%d,%d", params.width, params.height, params.bps, params.fps));
                //setDecodingState(true);


                // get the video port and create the video connection
                videoPort = myConn.getVideoPort();
                videoConnection = new Connection(Pi_address, videoPort, Connection.CONNECT_TIMEOUT);
                if (!videoConnection.isConnected())
                {
                    throw new Exception();
                }

                buffer = new byte[BUFFER_SIZE];
                m_codec.start();
                inputBuffers = m_codec.getInputBuffers();
                presentationTimeInc = 1000000 / params.fps;

                // read from the source
                while (!isInterrupted())
                {
                    // read from the stream
                    int len = videoConnection.read(buffer);
                    if (isInterrupted()) break;
                    //Log.info(String.format("len = %d", len));

                    // process the input buffer
                    if (len > 0)
                    {
                        numReadErrors = 0;
                        for (int i = 0; i < len && !isInterrupted(); i++)
                        {
                            // add the byte to the NAL
                            if (nalLen == nal.length)
                            {
                                nal = Arrays.copyOf(nal, nal.length + NAL_SIZE_INC);
                                if (isInterrupted()) break;
                                //Log.info(String.format("NAL size: %d", nal.length));
                            }
                            nal[nalLen++] = buffer[i];

                            // process the byte
                            if (buffer[i] == 0)
                            {
                                numZeroes++;
                            }
                            else
                            {
                                if (buffer[i] == 1 && numZeroes == 3)
                                {
                                    // get the NAL type
                                    nalLen -= 4;
                                    int nalType = (nalLen > 4 && nal[0] == 0 && nal[1] == 0 && nal[2] == 0 && nal[3] == 1) ? (nal[4] & 0x1F) : -1;

                                    // process the first SPS record we encounter
                                    if (nalType == 7 && !gotSPS)
                                    {
                                        //hideMessage();
                                        //startVideoHandler.post(startVideoRunner);
                                        gotSPS = true;
                                        if (isInterrupted()) break;
                                    }

                                    // reset the buffer for invalid NALs
                                    if (nalType == -1)
                                    {
                                        nal[0] = nal[1] = nal[2] = 0;
                                        nal[3] = 1;
                                    }

                                    // process valid NALs after getting the first SPS record
                                    else if (gotSPS)
                                    {
                                        int index = m_codec.dequeueInputBuffer(0);
                                        if (isInterrupted()) break;
                                        if (index >= 0)
                                        {
                                            ByteBuffer inputBuffer = inputBuffers[index];
                                            //ByteBuffer inputBuffer = m_codec.getInputBuffer(index);
                                            inputBuffer.put(nal, 0, nalLen);
                                            if (isInterrupted()) break;
                                            m_codec.queueInputBuffer(index, 0, nalLen, presentationTime, 0);
                                            presentationTime += presentationTimeInc;
                                            if (isInterrupted()) break;
                                        }
                                        //Log.info(String.format("dequeueInputBuffer index = %d", index));
                                    }
                                    nalLen = 4;
                                }
                                numZeroes = 0;
                            }
                        }
                    }
                    else
                    {
                        numReadErrors++;
                        if (numReadErrors >= MAX_READ_ERRORS)
                        {
                            //System.out.println(" Error, lost connection");
                            Log.e("Decoder", "Error, lost connection");
                            break;
                        }
                        //Log.info("len == 0");
                    }

                    // send output buffers to the surface
                    if (gotSPS)
                    {
                        MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();
                        int index = m_codec.dequeueOutputBuffer(info, 0);
                        if (isInterrupted()) break;
                        while (index >= 0)
                        {
                            m_codec.releaseOutputBuffer(index, true);
                            if (isInterrupted()) break;
                            index = m_codec.dequeueOutputBuffer(info, 0);
                            if (isInterrupted()) break;
                        }
                        if (isInterrupted()) break;
                    }
                }
            }
            catch (Exception ex)
            {
                if (myConn == null || !myConn.isConnected() ||
                        videoConnection == null || !videoConnection.isConnected())
                {
                    Log.e("Decoder", "Couldn't connect.");
                    //finishHandler.postDelayed(finishRunner, FINISH_TIMEOUT);
                }
                else
                {
                    Log.e("Decoder", "Error, lost connection");
                }
                Log.e("Decoder", ex.toString());
                ex.printStackTrace();
            }

            // close everything
            cleanup();
        }

        public synchronized void cleanup()
        {
            // close the video connection
            if (videoConnection != null)
            {
                try
                {
                    videoConnection.close();
                    Log.i("Decoder","video connection closed");
                }
                catch (Exception ex) {}
                videoConnection = null;
            }

            // close the command connection
            if (myConn != null)
            {
                try
                {
                    myConn.close();
                    Log.i("Decoder","Connection closed");
                }
                catch (Exception ex) {}
                myConn = null;
            }

            // stop the decoder
            if (m_codec != null)
            {
                try
                {
                    //setDecodingState(false);
                    m_codec.stop();
                    m_codec.release();
                    Log.i("Decoder","decoder stopped, released");
                }
                catch (Exception ex) {}
                m_codec = null;
            }
        }


    }
}
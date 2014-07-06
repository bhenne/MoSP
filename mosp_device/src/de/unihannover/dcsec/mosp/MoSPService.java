package de.unihannover.dcsec.mosp;

import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.text.SimpleDateFormat;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import de.unihannover.dcsec.mosp.database.DbHelper;

import android.app.Notification;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.SharedPreferences.OnSharedPreferenceChangeListener;
import android.database.sqlite.SQLiteDatabase;
import android.graphics.BitmapFactory;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;
import android.os.IBinder;
import android.preference.PreferenceManager;
import android.util.Log;

public class MoSPService extends Service implements OnSharedPreferenceChangeListener {

	private static final String LOG = "MoSPService";
	
	private static final String HMAC_KEY = "omfgakeywtfdoidonow?";

	LocationManager locationManager;
	LocationListener locationListener;
	
	private NotificationManager mNotificationManager;
	private Notification notification;
	private static final int notificationID = 1;
	private static final int errorNotificationID = 2;
	
	private static final int MIN_SLEEP_TIME = 10 * 1000; // 10s in ms
	private static final int MIN_SLEEP_DISTANCE = 50; // meter

	private static final int maxConnectionTries = 10;
	
	private SharedPreferences prefs;

	private String hostAddress;
	private int hostPort;
	private int personID;
	
	private static String dateFormatString = "HH:mm:ss, dd.MM.yyyy";
	
	private DbHelper dbHelper;
	private SQLiteDatabase db;
	

	@Override
	public void onCreate() {
		super.onCreate();

		String ns = Context.NOTIFICATION_SERVICE;
		this.mNotificationManager = (NotificationManager) getSystemService(ns);

		this.prefs = PreferenceManager.getDefaultSharedPreferences(this);
		this.prefs.registerOnSharedPreferenceChangeListener(this);

		this.hostAddress = prefs.getString("address", "");
		this.hostPort = Integer.parseInt(prefs.getString("port", "-1"));
		this.personID = Integer.parseInt(prefs.getString("id", "-1"));
		
		this.dbHelper = new DbHelper(this);
		
		Notification.Builder nBuilder = new Notification.Builder(this);
		nBuilder = nBuilder.setContentIntent(PendingIntent.getActivity(
				this, 0, new Intent(this, MoSPMobileDeviceActivity.class), PendingIntent.FLAG_CANCEL_CURRENT))
				.setContentTitle(getText(R.string.notification_text))
				.setContentText(this.hostAddress + ":" + this.hostPort + ", ID " + this.personID)
				.setSmallIcon(R.drawable.ic_mosp_notification)
				.setLargeIcon(BitmapFactory.decodeResource(this.getResources(), R.drawable.ic_mosp_notification))
				.setOngoing(true)
				.setTicker(getText(R.string.notification_text)).setWhen(System.currentTimeMillis());
		Log.d(LOG, "built notification");
		this.notification = nBuilder.getNotification();
		Log.d(LOG, "got notification");

//		this.gatherer = new LocationGatherer();
		
		// Acquire a reference to the system Location Manager
		locationManager = (LocationManager) this.getSystemService(Context.LOCATION_SERVICE);

		// Define a listener that responds to location updates
		locationListener = new LocationListener() {
		    public void onLocationChanged(Location location) {
		      // Called when a new location is found by the network location provider.
		    	new LocationSender(location).start();
		    }

		    public void onStatusChanged(String provider, int status, Bundle extras) {}

		    public void onProviderEnabled(String provider) {}

		    public void onProviderDisabled(String provider) {}
		  };
		
		Log.d(LOG, "onCreate");
	}

	@Override
	public int onStartCommand(Intent intent, int flags, int startId) {
		super.onStartCommand(intent, flags, startId);

		this.locationManager.requestLocationUpdates(
				LocationManager.GPS_PROVIDER, MIN_SLEEP_TIME, MIN_SLEEP_DISTANCE, this.locationListener);
		this.locationManager.requestLocationUpdates(
				LocationManager.NETWORK_PROVIDER, MIN_SLEEP_TIME, MIN_SLEEP_DISTANCE, this.locationListener);
		
		Log.d(LOG, "onStartCommand");
		if(this.prefs.getBoolean("notification", true)) {
			this.startForeground(notificationID, this.notification);
//			this.mNotificationManager.notify(notificationID, notification);
		}

		return START_STICKY;
	}

	@Override
	public void onDestroy() {
		super.onDestroy();

		Log.d(LOG, "onDestroy");
		
		this.locationManager.removeUpdates(this.locationListener);

		this.mNotificationManager.cancel(notificationID);
		this.mNotificationManager.cancel(errorNotificationID);
	}

	@Override
	public IBinder onBind(Intent arg0) {
		return null;
	}

	public void onSharedPreferenceChanged(SharedPreferences sharedPreferences,
			String key) {
		if(key.equals("notification") && !sharedPreferences.getBoolean(key, true)) {
			// disable notification
			this.mNotificationManager.cancel(notificationID);
		} else if(key.equals("notification") && sharedPreferences.getBoolean(key, true)) {
			// enable notification
			this.mNotificationManager.notify(notificationID, notification);
		}
	}

	class LocationSender extends Thread {
		
		Location location;
		
		public LocationSender(Location location) {
			this.location = location;
		}
		
		public void run() {
			double lat = location.getLatitude();
			double lon = location.getLongitude();
			float acc = location.getAccuracy();
			
			String urlString = hostAddress + ":" + hostPort;
			urlString += "/location?id=" + personID;
			urlString += "&lat=" + lat;
			urlString += "&lon=" + lon;
			urlString += "&acc=" + acc;
			
			SecretKeySpec keySpec = new SecretKeySpec(
	                HMAC_KEY.getBytes(),
	                "HmacSHA256");
	        Mac mac;
			try {
				mac = Mac.getInstance("HmacSHA256");
			} catch (NoSuchAlgorithmException e1) {
				Log.e(LOG, e1.getMessage());
				return;
			}
	        try {
				mac.init(keySpec);
			} catch (InvalidKeyException e1) {
				Log.e(LOG, e1.getMessage());
				return;
			}
	        byte[] rawHmac = mac.doFinal(("" + personID + lat + lon)
	        		.getBytes());

	        StringBuilder sb = new StringBuilder(rawHmac.length * 2);
	        for (int i = 0; i < rawHmac.length; i++) {
	            sb.append(Character.forDigit((rawHmac[i] & 0xf0) >> 4, 16));
	            sb.append(Character.forDigit(rawHmac[i] & 0x0f, 16));
	        }
	        urlString += "&hmac=" + sb.toString(); 
			
			URL url;
			Log.d(LOG, "Trying to send location with URL " + urlString);
			try {
				url = new URL(urlString);
//				url = new URL("http://www.google.com");
			} catch (MalformedURLException e) {
				showErrorNotification(MoSPService.this.getString(R.string.invalidHostTitle),
						MoSPService.this.getString(R.string.invalidHostInfo));
				Log.e(LOG, e.getMessage());
				saveReport(lat, lon, acc, MoSPService.this.getString(R.string.invalidHostTitle) + " " + e.getMessage());
				return;
			}
			HttpURLConnection urlConnection;
			String serverResponse;
			try {
				urlConnection = (HttpURLConnection) url.openConnection();
				serverResponse = "" + urlConnection.getResponseCode() + " " + urlConnection.getResponseMessage();
				Log.d(LOG, "Response Code + response Message: " + urlConnection.getResponseCode() + " " 
						+ urlConnection.getResponseMessage());
				urlConnection.disconnect();
			} catch (IOException e) {
				Log.e(LOG, "Error while connectiong to " + url.toString());
				Log.e(LOG, e.getMessage());
				showErrorNotification(MoSPService.this.getString(R.string.errorConnectionTitle),
						MoSPService.this.getString(R.string.errorConnectionInfo));
				saveReport(lat, lon, acc, MoSPService.this.getString(R.string.errorConnectionTitle) + " " + e.getMessage());
				return;
			}
			saveReport(lat, lon, acc, serverResponse);
			mNotificationManager.cancel(errorNotificationID);
		}
	}
	
	private void saveReport(double latitude, double longitude,
			float accuracy, String status) {

		String now = new SimpleDateFormat(dateFormatString)
								.format(System.currentTimeMillis());
		
		db = this.dbHelper.getWritableDatabase();
		
		ContentValues values = new ContentValues();
		values.put(DbHelper.C_CREATED_AT, now);
		values.put(DbHelper.C_PERSON_ID, this.personID);
		values.put(DbHelper.C_LAT, latitude);
		values.put(DbHelper.C_LON, longitude);
		values.put(DbHelper.C_ACCURACY, accuracy);
		values.put(DbHelper.C_STATUS, status);
		
		db.insert(DbHelper.TABLE, null, values);
		db.close();
		Log.d(LOG, "inserted " + values.toString());
		
	}

	private void showErrorNotification(String title, String message) {
		Notification.Builder nBuilder = new Notification.Builder(this);
		nBuilder = nBuilder.setContentIntent(PendingIntent.getActivity(
				this, 0, new Intent(this, MoSPMobileDeviceActivity.class), PendingIntent.FLAG_CANCEL_CURRENT))
				.setContentTitle(title)
				.setContentText(message)
				.setSmallIcon(R.drawable.ic_mosp_notification)
				.setLargeIcon(BitmapFactory.decodeResource(this.getResources(), R.drawable.ic_mosp_notification))
				.setTicker(title).setWhen(System.currentTimeMillis());
		Notification errorNotification = nBuilder.getNotification();
		MoSPService.this.mNotificationManager.notify(errorNotificationID, errorNotification);
	}
}

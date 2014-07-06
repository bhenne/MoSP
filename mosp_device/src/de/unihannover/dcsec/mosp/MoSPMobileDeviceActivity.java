package de.unihannover.dcsec.mosp;

import de.unihannover.dcsec.mosp.database.DbHelper;
import android.app.Activity;
import android.app.ActivityManager;
import android.app.AlertDialog;
import android.app.ActivityManager.RunningServiceInfo;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.SharedPreferences.Editor;
import android.content.SharedPreferences.OnSharedPreferenceChangeListener;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.util.Log;
import android.view.Menu;
import android.view.MenuInflater;
import android.view.MenuItem;
import android.view.View;
import android.widget.CompoundButton;
import android.widget.CompoundButton.OnCheckedChangeListener;
import android.widget.ListView;
import android.widget.SimpleCursorAdapter;
import android.widget.TextView;
import android.widget.SimpleCursorAdapter.ViewBinder;
import android.widget.Switch;

public class MoSPMobileDeviceActivity extends Activity implements OnCheckedChangeListener, 
																OnSharedPreferenceChangeListener {
	
	private static final String TAG = "MoSPMobileDeviceActivity";
	
	private Switch serviceSwitch;
	
	private SharedPreferences prefs;
	
	private String hostAddress;
	private int hostPort;
	private int personID;
	
	private DbHelper dbHelper;
	private SQLiteDatabase db;
	public Cursor cursor;
	public ListView list;
	private SimpleCursorAdapter adapter;
	static final String[] FROM = {DbHelper.C_CREATED_AT, DbHelper.C_PERSON_ID, DbHelper.C_LAT,
		DbHelper.C_LON, DbHelper.C_ACCURACY, DbHelper.C_STATUS};
	static final int[] TO = {R.id.textCreatedAt, R.id.textPersonID, R.id.textLatitude,
		R.id.textLongitude, R.id.textAccuracy, R.id.textServerResponse};
	
	
    /** Called when the activity is first created. */
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.main);

        list = (ListView) findViewById(R.id.overviewList);
        
        dbHelper = new DbHelper(this);
        db = dbHelper.getReadableDatabase();
        
        this.prefs = PreferenceManager.getDefaultSharedPreferences(this);
		this.prefs.registerOnSharedPreferenceChangeListener(this);
		
        this.hostAddress = prefs.getString("address", "");
        this.hostPort = Integer.parseInt(prefs.getString("port", "-1"));
		this.personID = Integer.parseInt(prefs.getString("id", "-1"));
		
        this.serviceSwitch = (Switch) findViewById(R.id.serviceSwitch);
        this.serviceSwitch.setChecked(this.serviceRunning());
        this.serviceSwitch.setOnCheckedChangeListener(this);
    }
    
	
	@Override
	protected void onResume() {
		super.onResume();
		
		this.cursor = db.query(DbHelper.TABLE, null, null, null, null, null, DbHelper.C_CREATED_AT + " DESC LIMIT 100");
		startManagingCursor(cursor);
		
		this.adapter = new SimpleCursorAdapter(this, R.layout.row, cursor, FROM, TO);
		this.adapter.setViewBinder(VIEW_BINDER);
		this.list.setAdapter(adapter);
	}

    
    @Override
    public void onDestroy() {
    	super.onDestroy();
    	
    	db.close();
    }
    
    private boolean serviceRunning() {
        ActivityManager manager = (ActivityManager) getSystemService(ACTIVITY_SERVICE);
        for (RunningServiceInfo service : manager.getRunningServices(Integer.MAX_VALUE)) {
            if ("de.unihannover.dcsec.mosp.MoSPService".equals(service.service.getClassName())) {
                return true;
            }
        }
        return false;
    }

	public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
		switch (buttonView.getId()) {
		case R.id.serviceSwitch:
			Log.d(TAG, "switch changed to " + isChecked);
			if(isChecked) {
				if(this.hostAddress.length() == 0 || this.hostPort == -1 || this.personID == -1) {
					AlertDialog.Builder builder = new AlertDialog.Builder(this).setTitle(R.string.invalidHostTitle)
							.setMessage(R.string.invalidHostInfo)
							.setPositiveButton("OK", new DialogInterface.OnClickListener() {
								public void onClick(DialogInterface dialog, int which) {
									dialog.dismiss();
								}
							});
					buttonView.setChecked(false);
					builder.show();
				} else {
					Log.d(TAG, "starting service");
					startService(new Intent(this, MoSPService.class));
				}
			} else {
				Log.d(TAG, "stopping service");
				stopService(new Intent(this, MoSPService.class));
			}
			Log.d(TAG, "Service running? " + this.serviceRunning());
			break;

		default:
			break;
		}	
	}

	@Override
	public boolean onCreateOptionsMenu(Menu menu) {
		MenuInflater inflater = getMenuInflater();
		inflater.inflate(R.menu.main_menu, menu);
		return true;
	}
	
	@Override
	public boolean onOptionsItemSelected(MenuItem item) {
		switch (item.getItemId()) {
		case R.id.itemPrefs:
			Log.d(TAG, "settings selected");
			startActivity(new Intent(this, PrefsActivity.class));
			break;
		case R.id.itemRefresh:
			Log.d(TAG, "refresh listView");
			this.list.invalidateViews();
			this.cursor.requery();
			break;
		case R.id.itemClear:
			Log.d(TAG, "clear Database");
//			this.db.close();
//			SQLiteDatabase clearDB = this.dbHelper.getWritableDatabase();
			this.dbHelper.clearDB();
//			clearDB.close();
//			this.db = this.dbHelper.getReadableDatabase();
			this.list.invalidateViews();
			this.cursor.requery();
			break;
		default:
			Log.d(TAG, "unknown options menu item: " + item.getItemId());
			break;
		}
		return true;
	}

	public void onSharedPreferenceChanged(SharedPreferences sharedPreferences,
			String key) {
		if(key.equals("address")) {
			String value = sharedPreferences.getString(key, "");
			if(!value.startsWith("http://")) {
	        	value = "http://" + value;
	        }
			Editor editor = sharedPreferences.edit();
			editor.putString("address", value);
			editor.commit();
		}
		this.hostAddress = prefs.getString("address", "");
        this.hostPort = Integer.parseInt(prefs.getString("port", "-1"));
        this.personID = Integer.parseInt(prefs.getString("id", "-1"));
	}

	static final ViewBinder VIEW_BINDER = new ViewBinder() {
		
		
		public boolean setViewValue(View view, Cursor cursor, int columnIndex) {
			switch (view.getId()) {
			case R.id.textPersonID:
				int persID = cursor.getInt(cursor.getColumnIndex(DbHelper.C_PERSON_ID));
				((TextView) view).setText("Person ID: " + persID);
				return true;
			case R.id.textLatitude:
				String lat = cursor.getString(cursor.getColumnIndex(DbHelper.C_LAT));
				((TextView) view).setText("Lat: " + lat);
				return true;
			case R.id.textLongitude:
				String lon = cursor.getString(cursor.getColumnIndex(DbHelper.C_LON));
				((TextView) view).setText("Lon: " + lon);
				return true;
			case R.id.textAccuracy:
				String acc = cursor.getString(cursor.getColumnIndex(DbHelper.C_ACCURACY));
				((TextView) view).setText("Accuracy: " + acc);
				return true;
			case R.id.textServerResponse:
				String serverResponse = cursor.getString(cursor.getColumnIndex(DbHelper.C_STATUS));
				((TextView) view).setText("Status: " + serverResponse);
				return true;
			default:
				return false;
			}
		}
	};

}
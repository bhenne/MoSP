package de.unihannover.dcsec.mosp.database;

import android.content.Context;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.provider.BaseColumns;
import android.util.Log;

public class DbHelper extends SQLiteOpenHelper {

	static final String TAG = "DbHelper";
	static final String DB_NAME = "reports.db";
	static final int DB_VERSION = 2;
	
	public static final String TABLE = "reports";
	static final String C_ID = BaseColumns._ID;
	public static final String C_CREATED_AT = "created_at";
	public static final String C_PERSON_ID = "person_id";
	public static final String C_LAT = "latitude";
	public static final String C_LON = "longitude";
	public static final String C_ACCURACY = "accuracy";
	public static final String C_STATUS = "status";
	
	Context context;
	
	public DbHelper(Context context) {
		super(context, DB_NAME, null, DB_VERSION);
		this.context = context;
	}
	
	@Override
	public void onCreate(SQLiteDatabase db) {
		String sql = "create table " + TABLE + " ("
				+ C_ID + " INTEGER PRIMARY KEY autoincrement, "
				+ C_CREATED_AT + " TEXT, "
				+ C_PERSON_ID + " INTEGER, "
				+ C_LAT + " REAL, "
				+ C_LON + " REAL, "
				+ C_ACCURACY + " INTEGER, "
				+ C_STATUS + " TEXT)";
		db.execSQL(sql);
		Log.d(TAG, "created db with: " + sql);
	}

	@Override
	public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
		// TODO replace with ALTER TABLE, for now the database is just replaced
		db.execSQL("drop table if exists " + TABLE);
		Log.d(TAG, "onUpdate");
		onCreate(db);
	}
	
	public void clearDB() {
		SQLiteDatabase db = this.getWritableDatabase();
		db.execSQL("drop table if exists " + TABLE);
		onCreate(db);
	}

}

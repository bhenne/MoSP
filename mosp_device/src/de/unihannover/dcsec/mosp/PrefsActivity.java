package de.unihannover.dcsec.mosp;

import android.os.Bundle;
import android.preference.PreferenceActivity;

/**
 * Preference activity for settings by user.
 * 
 * @author philipp
 *
 */
public class PrefsActivity extends PreferenceActivity {

	@Override
	protected void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);
		addPreferencesFromResource(R.xml.prefs);
	}
}

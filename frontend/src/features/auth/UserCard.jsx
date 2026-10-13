import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useUserData } from './UserDataContext.jsx';
import { useVehicle } from '../vehicles/VehicleContext.jsx';

export function UserCard({ username: propUsername, onLogout }) {
  const [open, setOpen] = useState(false);
  const [showPreferences, setShowPreferences] = useState(false);
  const [savingPreferences, setSavingPreferences] = useState(false);
  const [preferencesError, setPreferencesError] = useState('');
  const containerRef = useRef(null);
  const {
    userData,
    loading,
    logout: contextLogout,
    updatePreferences,
  } = useUserData();
  const { clearSelectedVehicle } = useVehicle();
  const [preferences, setPreferences] = useState({
    age_group: '',
    driver_type: '',
    road_conditions: [''],
    tolls: '',
  });

  const displayName = propUsername ?? userData?.username ?? userData?.name ?? localStorage.getItem('username') ?? (loading ? 'Loading...' : 'User');
  const email = userData?.email ?? '';

  const openPreferences = () => {
    const currentPreferences = userData?.preferences ?? {};
    setPreferences({
      age_group: currentPreferences.age_group ?? '',
      driver_type: currentPreferences.driver_type ?? '',
      road_conditions: [currentPreferences.road_conditions?.[0] ?? ''],
      tolls: currentPreferences.tolls === undefined
        ? ''
        : String(currentPreferences.tolls),
    });
    setPreferencesError('');
    setOpen(false);
    setShowPreferences(true);
  };

  const savePreferences = async (event) => {
    event.preventDefault();
    setSavingPreferences(true);
    setPreferencesError('');

    try {
      await updatePreferences({
        ...preferences,
        road_conditions: preferences.road_conditions,
        tolls: preferences.tolls === 'true',
      });
      setShowPreferences(false);
    } catch (error) {
      setPreferencesError(error.message);
    } finally {
      setSavingPreferences(false);
    }
  };

  useEffect(() => {
    function handleDocClick(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('click', handleDocClick);
    return () => document.removeEventListener('click', handleDocClick);
  }, []);

  const handleLogout = () => {
    setOpen(false);
    if (typeof onLogout === 'function') {
      onLogout();
      return;
    }

    if (typeof contextLogout === 'function') {
      contextLogout();
      return;
    }

    try {
      localStorage.removeItem('token');
    } catch (e) {}
    window.location.reload();
  };

  return (
    <div ref={containerRef} className="relative inline-block">
      <button
        type="button"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="border border-white  p-1 rounded-xl hover:bg-white/40 backdrop-blur-xs bg-white/20 h-full"
        title="User menu"
      >
        {/* simple user SVG avatar */}
        <svg className="w-8 h-8 text-white" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
          <circle cx="12" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.2" />
          <path d="M4 20c0-3.3137 2.6863-6 6-6h4c3.3137 0 6 2.6863 6 6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 mt-4 w-56 bg-white/20 backdrop-blur-2xl border border-white rounded-md shadow-lg z-50 overflow-hidden"
        >
          <div className="px-4 py-3 text-sm text-white border-b border-gray-100 backdrop-blur-3xl">
            <div className="font-bold text-gray-300">{displayName}</div>
            {email && <div className="mt-1 text-xs text-gray-400">{email}</div>}
            {!email && loading && <div className="mt-1 text-xs text-gray-300 ">Loading email...</div>}
          </div>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              clearSelectedVehicle();
            }}
            className="w-full text-left px-4 py-2 text-sm text-white hover:bg-gray-50/20 backdrop-blur-3xl"
          >
            Change car
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={openPreferences}
            className="w-full text-left px-4 py-2 text-sm text-white hover:bg-gray-50/20 backdrop-blur-3xl"
          >
            Change preferences
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={handleLogout}
            className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-50/20 backdrop-blur-3xl"
          >
            Logout
          </button>
        </div>
      )}

      {showPreferences && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/20 backdrop-blur-xl p-4">
          <form
            onSubmit={savePreferences}
            className="max-h-[calc(100vh-2rem)] w-full max-w-sm overflow-y-auto rounded-xl border border-white bg-slate-900/80 p-6 text-white shadow-2xl backdrop-blur-xl"
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold">Change preferences</h2>
              <button
                type="button"
                onClick={() => setShowPreferences(false)}
                className="text-2xl leading-none text-white/80 hover:text-white"
                aria-label="Close preferences"
              >
                &times;
              </button>
            </div>

            <label className="mb-3 block text-sm">
              Age group
              <select
                required
                value={preferences.age_group}
                onChange={(event) => setPreferences({
                  ...preferences,
                  age_group: event.target.value,
                })}
                className="mt-1 w-full rounded border border-white/60 bg-white p-2 text-gray-900"
              >
                <option value="">Select an age group</option>
                <option value="young">Young (18-29)</option>
                <option value="adult">Adult (30-59)</option>
                <option value="senior">Senior (60+)</option>
              </select>
            </label>

            <label className="mb-3 block text-sm">
              Driving style
              <select
                required
                value={preferences.driver_type}
                onChange={(event) => setPreferences({
                  ...preferences,
                  driver_type: event.target.value,
                })}
                className="mt-1 w-full rounded border border-white/60 bg-white p-2 text-gray-900"
              >
                <option value="">Select a driving style</option>
                <option value="calm">Calm</option>
                <option value="fast">Fast</option>
                <option value="efficient">Efficient</option>
              </select>
            </label>

            <label className="mb-3 block text-sm">
              Road conditions
              <select
                required
                value={preferences.road_conditions[0]}
                onChange={(event) => setPreferences({
                  ...preferences,
                  road_conditions: [event.target.value],
                })}
                className="mt-1 w-full rounded border border-white/60 bg-white p-2 text-gray-900"
              >
                <option value="">Select road conditions</option>
                <option value="highway_roads">Highway roads</option>
                <option value="city_roads">City roads</option>
                <option value="dirt_roads">Dirt roads</option>
                <option value="mixed">A mix of roads</option>
              </select>
            </label>

            <label className="mb-4 block text-sm">
              Toll roads acceptable?
              <select
                required
                value={preferences.tolls}
                onChange={(event) => setPreferences({
                  ...preferences,
                  tolls: event.target.value,
                })}
                className="mt-1 w-full rounded border border-white/60 bg-white p-2 text-gray-900"
              >
                <option value="">Select an option</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </label>

            {preferencesError && (
              <p className="mb-3 text-sm text-red-300">{preferencesError}</p>
            )}
            <button
              type="submit"
              disabled={savingPreferences}
              className="w-full rounded bg-white px-3 py-2 font-semibold text-gray-900 disabled:opacity-50"
            >
              {savingPreferences ? 'Saving...' : 'Save preferences'}
            </button>
          </form>
        </div>,
        document.body,
      )}
    </div>
  );
}

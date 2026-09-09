/**
 * Aurora.jsx — Compatibility wrapper for OrbScene.
 * 
 * The Python layer and App.jsx call this component with the same
 * props as before: `state` (sleep | awake | listening) and `style`.
 * We simply forward them to the new 3D OrbScene.
 */
import React from 'react';
import OrbScene from './OrbScene';

const Aurora = ({ state = 'awake', style }) => (
  <OrbScene state={state} style={style} />
);

export default Aurora;

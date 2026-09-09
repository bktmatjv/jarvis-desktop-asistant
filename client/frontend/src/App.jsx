import React, { useState, useEffect } from 'react';
import Aurora from './components/Aurora';
import './App.css';

function App() {
  const [orbState, setOrbState] = useState("sleep"); // sleep, awake, listening
  const [adminVisible, setAdminVisible] = useState(false);
  
  // Settings for Hotkeys
  const [hotkey, setHotkey] = useState("ctrl+space");

  useEffect(() => {
    // Escuchadores globales (llamados por PyWebView)
    window.wakeUpUI = () => setOrbState("awake");
    window.listeningUI = () => setOrbState("listening");
    window.resetHUD = () => setOrbState("awake");
    window.sleepUI = () => setOrbState("sleep");
    
    // Si necesitas recibir el hotkey actual desde Python:
    window.setHotkey = (key) => setHotkey(key);
  }, []);

  const saveHotkey = () => {
    // Envia el nuevo hotkey a Python si pywebview está disponible
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.update_hotkey(hotkey);
    }
    alert(`Hotkey actualizado a: ${hotkey}`);
  };

  // Usar hash en lugar de query string porque file:// no soporta querystrings en Windows
  const isOrbMode = window.location.hash.includes("mode=orb");

  useEffect(() => {
    if (isOrbMode) {
        document.body.classList.add("orb-mode");
        document.documentElement.classList.add("orb-mode"); // También <html>
    } else {
        document.body.classList.remove("orb-mode");
        document.documentElement.classList.remove("orb-mode");
    }
  }, [isOrbMode]);

  if (isOrbMode) {
    return (
      <Aurora 
        state={orbState} 
      />
    );
  }

  return (
    <>
      <div className="crt-overlay"></div>
      
      <div className="app-container">
        
        {/* HEADER */}
        <header className="header">
            <div className="logo-area">
                <span className="logo-title">JARVIS</span>
                <span className="logo-subtitle">JUST A RATHER VERY<br/>INTELLIGENT SYSTEM</span>
            </div>
            <div className="header-icons">
                <div className="icon-btn active">[MIC]</div>
                <div className="icon-btn active">[VOL]</div>
                <div className="icon-btn active" onClick={() => setAdminVisible(!adminVisible)}>[CFG]</div>
            </div>
        </header>

        {/* MAIN GRID - HUD */}
        <main className="main-grid">
            
            {/* COLUMN 1: Telemetry */}
            <div className="col-left">
                <section className="panel">
                    <div className="panel-header">PERFIL DE USUARIO</div>
                    <div style={{ padding: '15px' }}>
                        <div style={{ fontSize: '16px', fontWeight: 'bold' }}>USUARIO MAESTRO</div>
                        <div style={{ color: 'var(--jarvis-green)' }}>ONLINE</div>
                        <button className="btn-outline" onClick={() => setAdminVisible(!adminVisible)} style={{ marginTop: '10px', position: 'static' }}>
                          [ ADMIN ]
                        </button>
                    </div>
                </section>

                <section className="panel" style={{ flexGrow: 1 }}>
                    <div className="panel-header">TELEMETRIA</div>
                    <div style={{ padding: '15px' }}>
                        <p>CPU: 45%</p>
                        <p>RAM: 60%</p>
                    </div>
                </section>
            </div>

            {/* COLUMN 2: Central AI */}
            <div className="col-center" style={{ position: 'relative' }}>
                <section className="panel" style={{ flex: 1 }}>
                    <div className="panel-header">CEREBRO CENTRAL - IA</div>
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', opacity: 0.5 }}>
                        NO SIGNAL - HUD MODE
                    </div>
                </section>

                <section className="panel chat-panel">
                    <div className="panel-header">CHAT / INTERACCION</div>
                    <div style={{ padding: '15px', flex: 1, overflowY: 'auto' }}>
                        <div style={{ color: 'var(--jarvis-cyan)' }}>[SYSTEM] Jarvis en espera...</div>
                    </div>
                </section>
            </div>

            {/* COLUMN 3: Global */}
            <div className="col-right">
                <section className="panel" style={{ height: '200px' }}>
                    <div className="panel-header">ESTADO MODULOS</div>
                    <div style={{ padding: '15px' }}>
                        <p>[V] VOZ <span className="green">OPERATIVO</span></p>
                        <p>[D] DATOS <span className="green">OPERATIVO</span></p>
                        <p>[S] SEGURIDAD <span className="green">OPERATIVO</span></p>
                    </div>
                </section>
            </div>
        </main>

        {/* BOTTOM MODALS */}
        {adminVisible && (
          <div className="bottom-modals">
              <section className="panel admin-panel">
                  <div className="panel-header">
                    DASHBOARD ADMIN 
                    <button onClick={() => setAdminVisible(false)} style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer' }}>X</button>
                  </div>
                  <div className="admin-content" style={{ marginTop: '15px' }}>
                      <div className="admin-stat-box">
                          <div className="label">ESTADO DE SISTEMA</div>
                          <div className="val green">OPTIMO</div>
                      </div>
                      
                      {/* CONFIGURACIÓN DE TECLAS */}
                      <div className="admin-stat-box" style={{ flex: 2, textAlign: 'left' }}>
                          <div className="label" style={{ marginBottom: '10px' }}>CONFIGURACIÓN DE TECLAS (HOTKEYS)</div>
                          <div className="form-group">
                              <label>Atajo de Activación de Jarvis (ej: ctrl+space):</label>
                              <div style={{ display: 'flex', gap: '10px' }}>
                                <input 
                                    type="text" 
                                    className="hotkey-input"
                                    value={hotkey}
                                    onChange={(e) => setHotkey(e.target.value)}
                                    placeholder="ctrl+space"
                                />
                                <button className="btn-solid" onClick={saveHotkey}>GUARDAR</button>
                              </div>
                          </div>
                      </div>
                  </div>
              </section>
          </div>
        )}
      </div>

      {/* AURORA COMPONENT IN PANEL MODE */}
      <Aurora 
        state={orbState} 
        style={{
            width: '200px',
            height: '200px',
            bottom: '20px',
            left: '20px',
            top: 'auto',
            borderRadius: '50%',
            position: 'fixed'
        }}
      />
    </>
  );
}

export default App;

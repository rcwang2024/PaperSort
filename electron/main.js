const { app, BrowserWindow, dialog, Menu, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const isDev = require('electron-is-dev');
const http = require('http');
const DependencyChecker = require('./dependency-checker');

let mainWindow;
let backendProcess = null;
let frontendProcess = null;

// Kill any existing process on port 8000
async function killExistingBackend() {
  return new Promise((resolve) => {
    const { exec } = require('child_process');

    // Find process using port 8000
    exec('lsof -ti :8000', (error, stdout) => {
      if (error || !stdout.trim()) {
        // No process found or error - port is free
        console.log('Port 8000 is free');
        resolve();
        return;
      }

      const pid = stdout.trim();
      console.log(`Found existing process on port 8000 (PID: ${pid}), killing it...`);

      // Force kill the process (SIGKILL)
      exec(`kill -9 ${pid}`, (killError) => {
        if (killError) {
          console.error('Failed to kill existing process:', killError);
          // Try to continue anyway
          setTimeout(resolve, 2000);
        } else {
          console.log('Successfully killed existing backend process');

          // Verify port is free before continuing
          const verifyFree = () => {
            exec('lsof -ti :8000', (err, out) => {
              if (err || !out.trim()) {
                console.log('✓ Port 8000 verified free');
                resolve();
              } else {
                // Port still in use, wait a bit more
                console.log('Waiting for port to be freed...');
                setTimeout(verifyFree, 500);
              }
            });
          };

          setTimeout(verifyFree, 1000);
        }
      });
    });
  });
}

// Check if backend is running
function checkBackend(retries = 30) {
  return new Promise((resolve) => {
    const checkServer = (attempt) => {
      const req = http.get('http://127.0.0.1:8000/health', (res) => {
        if (res.statusCode === 200) {
          console.log('Backend is ready');
          resolve(true);
        } else if (attempt < retries) {
          setTimeout(() => checkServer(attempt + 1), 1000);
        } else {
          resolve(false);
        }
      });

      req.on('error', () => {
        if (attempt < retries) {
          setTimeout(() => checkServer(attempt + 1), 1000);
        } else {
          resolve(false);
        }
      });

      req.setTimeout(2000, () => {
        req.destroy();
        if (attempt < retries) {
          setTimeout(() => checkServer(attempt + 1), 1000);
        } else {
          resolve(false);
        }
      });
    };

    checkServer(0);
  });
}

// Check if Ollama is running
async function checkOllama() {
  return new Promise((resolve) => {
    const req = http.get('http://127.0.0.1:11434/api/version', (res) => {
      resolve(res.statusCode === 200);
    });

    req.on('error', () => resolve(false));
    req.setTimeout(2000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

// Start Python backend
async function startBackend() {
  // First, kill any existing backend process on port 8000
  await killExistingBackend();

  const fs = require('fs');
  const backendPath = isDev
    ? path.join(__dirname, '..', 'backend')
    : path.join(process.resourcesPath, 'backend');

  console.log('Starting backend from:', backendPath);
  console.log('Is development mode:', isDev);
  console.log('Resources path:', process.resourcesPath);

  // Check for bundled executable first (for production)
  const bundledExe = path.join(backendPath, 'dist', 'papersort-backend');

  if (!isDev && fs.existsSync(bundledExe)) {
    // Use bundled executable in production
    console.log('Using bundled backend executable:', bundledExe);

    backendProcess = spawn(bundledExe, [], {
      stdio: 'pipe',
      env: { ...process.env }
    });
  } else {
    // Fall back to Python script (development mode or if bundled exe not found)
    const launcherScript = path.join(backendPath, 'run_backend.sh');
    console.log('Using launcher script:', launcherScript);

    // Check if the script exists
    if (!fs.existsSync(launcherScript)) {
      console.error('Backend launcher script not found at:', launcherScript);
      dialog.showErrorBox(
        'Backend Error',
        `Backend launcher script not found at:\n${launcherScript}\n\nBackend path: ${backendPath}`
      );
      return false;
    }

    console.log('Backend script exists, starting...');

    backendProcess = spawn('bash', [launcherScript], {
      cwd: backendPath,
      stdio: 'pipe',
      env: { ...process.env }
    });
  }

  let backendOutput = '';
  let backendErrors = '';

  backendProcess.stdout.on('data', (data) => {
    const output = data.toString();
    backendOutput += output;
    console.log(`Backend: ${output}`);
  });

  backendProcess.stderr.on('data', (data) => {
    const error = data.toString();
    backendErrors += error;
    console.error(`Backend Error: ${error}`);
  });

  backendProcess.on('close', (code) => {
    console.log(`Backend process exited with code ${code}`);
    if (code !== 0 && code !== null) {
      const errorMsg = backendErrors || backendOutput || 'Unknown error';
      dialog.showErrorBox(
        'Backend Error',
        `The backend server failed to start (exit code: ${code}).\n\nError output:\n${errorMsg.substring(0, 500)}`
      );
    }
  });

  // Wait for backend to be ready (first launch with package install may take longer)
  console.log('Waiting for backend to be ready...');
  const isReady = await checkBackend(120); // 120 retries = 2 minutes max

  if (!isReady) {
    const errorDetails = backendErrors || backendOutput || 'No output captured';
    console.error('Backend failed to start. Output:', errorDetails);

    dialog.showErrorBox(
      'Backend Failed',
      `Could not connect to the backend server.\n\nBackend path: ${backendPath}\n\nOutput:\n${errorDetails.substring(0, 400)}\n\nPlease ensure:\n1. Python 3.8+ is installed\n2. Run: pip install -r requirements.txt`
    );
  } else {
    console.log('Backend started successfully!');
  }

  return isReady;
}

// Start frontend dev server (only in development)
async function startFrontend() {
  if (!isDev) return; // In production, we use built files

  const frontendPath = path.join(__dirname, '..', 'frontend');

  console.log('Starting frontend dev server from:', frontendPath);

  frontendProcess = spawn('npm', ['run', 'dev'], {
    cwd: frontendPath,
    stdio: 'pipe',
    shell: true
  });

  frontendProcess.stdout.on('data', (data) => {
    console.log(`Frontend: ${data}`);
  });

  frontendProcess.stderr.on('data', (data) => {
    console.error(`Frontend: ${data}`);
  });

  frontendProcess.on('close', (code) => {
    console.log(`Frontend process exited with code ${code}`);
  });

  // Wait a bit for Vite to start
  await new Promise(resolve => setTimeout(resolve, 3000));
}

// Create main window
async function createWindow() {
  const fs = require('fs');
  const os = require('os');

  // Check if dependencies were already verified (skip repeated checks)
  const markerFile = path.join(os.homedir(), '.papersort', '.deps_verified');
  const depsAlreadyVerified = fs.existsSync(markerFile);

  let checkResult;

  if (!depsAlreadyVerified) {
    console.log('First run - checking dependencies...');
    // Check dependencies first (Python, pip, packages, Graphviz, etc.)
    const checker = new DependencyChecker();
    checkResult = await checker.checkAll();

    if (!checkResult.allRequired) {
      // Show installation dialog
      const installResult = await checker.showInstallDialog(null);

      if (installResult.action === 'quit') {
        app.quit();
        return;
      } else if (installResult.action === 'restart') {
        // User completed installation - create marker before restart
        // This prevents asking again after restart
        const markerDir = path.join(os.homedir(), '.papersort');
        if (!fs.existsSync(markerDir)) {
          fs.mkdirSync(markerDir, { recursive: true });
        }
        fs.writeFileSync(markerFile, new Date().toISOString());
        console.log('✓ Installation completed, marker created');

        app.relaunch();
        app.quit();
        return;
      }
      // If 'continue', create marker too (user chose to skip)
      const markerDir = path.join(os.homedir(), '.papersort');
      if (!fs.existsSync(markerDir)) {
        fs.mkdirSync(markerDir, { recursive: true });
      }
      fs.writeFileSync(markerFile, new Date().toISOString());
      console.log('✓ User chose to continue, marker created');
    } else {
      // All required dependencies verified - create marker file
      const markerDir = path.join(os.homedir(), '.papersort');
      if (!fs.existsSync(markerDir)) {
        fs.mkdirSync(markerDir, { recursive: true });
      }
      fs.writeFileSync(markerFile, new Date().toISOString());
      console.log('✓ Dependencies verified, marker created');
    }
  } else {
    console.log('✓ Dependencies already verified (skipping check)');
    // Quick check - just verify Ollama status for optional features
    const checker = new DependencyChecker();
    checkResult = { results: { ollama: checker.commandExists('ollama') } };
  }

  // Check Ollama availability (optional, only ask once)
  const ollamaMarkerFile = path.join(os.homedir(), '.papersort', '.ollama_asked');
  const ollamaAlreadyAsked = fs.existsSync(ollamaMarkerFile);

  if (!ollamaAlreadyAsked && checkResult.results && !checkResult.results.ollama) {
    const response = await dialog.showMessageBox({
      type: 'info',
      title: 'Ollama Not Detected',
      message: 'Enable AI-powered features?',
      detail: 'Ollama provides advanced AI features:\n• Intelligent paper summaries\n• Analytical mind-maps\n• Better topic classification\n\nWithout Ollama, basic features will still work.\n\nInstall later: brew install ollama',
      buttons: ['Continue Without AI', 'Install Ollama', 'Quit'],
      defaultId: 0,
      cancelId: 2
    });

    // Mark that we asked about Ollama (don't ask again)
    fs.writeFileSync(ollamaMarkerFile, new Date().toISOString());

    if (response.response === 1) {
      // User wants to install Ollama
      require('child_process').exec('open -a Terminal.app');
      dialog.showMessageBox({
        type: 'info',
        message: 'Install Ollama',
        detail: 'Run these commands in Terminal:\n\nbrew install ollama\nollama pull llama3.2:3b\n\nThen restart PaperSort.',
        buttons: ['OK']
      });
      app.quit();
      return;
    } else if (response.response === 2) {
      app.quit();
      return;
    }
    // else: user chose "Continue Without AI" - proceed
  }

  // Start backend
  console.log('Starting backend...');
  await startBackend();

  // In development, start frontend dev server
  if (isDev) {
    console.log('Starting frontend dev server...');
    await startFrontend();
  }

  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    },
    title: 'PaperSort',
    titleBarStyle: 'default'
  });

  // Load the app
  let startUrl;
  if (isDev) {
    startUrl = 'http://localhost:1420'; // Vite dev server
  } else {
    // In production, frontend is packaged in app.asar or extraResources
    // Try multiple possible paths
    const possiblePaths = [
      path.join(__dirname, '..', 'frontend', 'dist', 'index.html'),
      path.join(process.resourcesPath, 'app.asar', 'frontend', 'dist', 'index.html'),
      path.join(process.resourcesPath, 'frontend', 'dist', 'index.html'),
    ];

    let frontendPath = null;
    for (const p of possiblePaths) {
      console.log('Checking frontend path:', p);
      if (require('fs').existsSync(p)) {
        frontendPath = p;
        console.log('✓ Found frontend at:', p);
        break;
      }
    }

    if (!frontendPath) {
      console.error('ERROR: Could not find frontend files!');
      console.error('Checked paths:', possiblePaths);
      dialog.showErrorBox(
        'Frontend Not Found',
        'Could not locate the frontend files.\n\nPaths checked:\n' + possiblePaths.join('\n')
      );
      frontendPath = possiblePaths[0]; // Use first path anyway
    }

    startUrl = `file://${frontendPath}`;
  }

  console.log('Loading URL:', startUrl);
  mainWindow.loadURL(startUrl);

  // Open DevTools only in development
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  // Create menu
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'Reload',
          accelerator: 'CmdOrCtrl+R',
          click: () => mainWindow.reload()
        },
        { type: 'separator' },
        { role: 'quit' }
      ]
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' }
      ]
    },
    {
      label: 'View',
      submenu: [
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' }
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'About PaperSort',
          click: async () => {
            await dialog.showMessageBox({
              type: 'info',
              title: 'About PaperSort',
              message: 'PaperSort v2.0.0',
              detail: 'AI-powered academic paper organizer with mind-maps\n\nPowered by Ollama'
            });
          }
        },
        { type: 'separator' },
        {
          label: 'Reset Dependency Check',
          click: async () => {
            const fs = require('fs');
            const os = require('os');

            const response = await dialog.showMessageBox({
              type: 'question',
              title: 'Reset Dependency Check',
              message: 'Reset dependency verification?',
              detail: 'This will make PaperSort check for dependencies again on next launch.\n\nUse this if you installed new dependencies or want to re-verify.',
              buttons: ['Cancel', 'Reset'],
              defaultId: 0,
              cancelId: 0
            });

            if (response.response === 1) {
              const markerFile = path.join(os.homedir(), '.papersort', '.deps_verified');
              const ollamaMarkerFile = path.join(os.homedir(), '.papersort', '.ollama_asked');

              try {
                if (fs.existsSync(markerFile)) fs.unlinkSync(markerFile);
                if (fs.existsSync(ollamaMarkerFile)) fs.unlinkSync(ollamaMarkerFile);

                await dialog.showMessageBox({
                  type: 'info',
                  message: 'Reset Complete',
                  detail: 'Dependency check will run on next app launch.\n\nRestart PaperSort now?',
                  buttons: ['Later', 'Restart Now']
                }).then(result => {
                  if (result.response === 1) {
                    app.relaunch();
                    app.quit();
                  }
                });
              } catch (err) {
                dialog.showErrorBox('Reset Failed', `Could not reset: ${err.message}`);
              }
            }
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);

  mainWindow.on('closed', () => {
    // On macOS, clean up backend when window closes
    // (app might still be running in dock but no UI)
    if (process.platform === 'darwin' && backendProcess) {
      console.log('Window closed on macOS, stopping backend...');
      backendProcess.kill('SIGTERM');
      if (frontendProcess) {
        frontendProcess.kill('SIGTERM');
      }
    }
    mainWindow = null;
  });
}

// Clean up processes on quit
app.on('will-quit', () => {
  if (backendProcess) {
    console.log('Stopping backend...');
    backendProcess.kill('SIGTERM');
    // Force kill if still running after 2 seconds
    setTimeout(() => {
      if (backendProcess && !backendProcess.killed) {
        console.log('Force killing backend...');
        backendProcess.kill('SIGKILL');
      }
    }, 2000);
  }
  if (frontendProcess) {
    console.log('Stopping frontend...');
    frontendProcess.kill('SIGTERM');
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

// IPC handlers
ipcMain.handle('dialog:openFolder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory']
  });

  if (result.canceled) {
    return null;
  }

  return result.filePaths[0];
});

// Start the app
app.whenReady().then(createWindow);

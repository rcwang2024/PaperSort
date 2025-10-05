// Type definitions for Electron API exposed via preload

export interface ElectronAPI {
  versions: {
    node: string;
    chrome: string;
    electron: string;
  };
  selectFolder: () => Promise<string | null>;
}

declare global {
  interface Window {
    electron?: ElectronAPI;
  }
}

export {};

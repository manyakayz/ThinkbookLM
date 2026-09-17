import { useState } from 'react';
import NotebookList from './components/NotebookList';
import DocumentList from './components/DocumentList';
import './index.css';

export default function App() {
  const [activeNotebook, setActiveNotebook] = useState(null);

  return (
    <div className="app-container">
      <NotebookList 
        activeNotebook={activeNotebook} 
        onSelectNotebook={setActiveNotebook} 
      />
      <main className="main-content">
        <DocumentList notebookId={activeNotebook} />
      </main>
    </div>
  );
}

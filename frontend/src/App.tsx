import { Route, Routes } from "react-router-dom";
import Layout from "./components/layout/Layout";
import HomePage from "./pages/HomePage";
import ProjectPage from "./pages/ProjectPage";
import TranslationPage from "./pages/TranslationPage";
import GlossaryPage from "./pages/GlossaryPage";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/projects/:projectId" element={<ProjectPage />} />
        <Route path="/projects/:projectId/translate" element={<TranslationPage />} />
        <Route path="/projects/:projectId/glossary" element={<GlossaryPage />} />
      </Routes>
    </Layout>
  );
}

export default App;

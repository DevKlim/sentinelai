
import { BrowserRouter, Routes, Route } from "react-router-dom";
import HomePage from "./src/pages/HomePage";
import Layout from "./src/components/Layout";

const App = () => (
  <BrowserRouter>
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
      </Routes>
    </Layout>
  </BrowserRouter>
);

export default App;

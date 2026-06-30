import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App", () => {
  it("renders login screen when token is missing", () => {
    localStorage.removeItem("contract_analysis_access_token");
    render(<App />);
    expect(screen.getByText(/Sign In/i)).toBeTruthy();
  });

  it("renders upload headline when authenticated", () => {
    localStorage.setItem("contract_analysis_access_token", "test-token");
    render(<App />);
    expect(screen.getByText(/Multi-Modal Contract Analysis Tool/i)).toBeTruthy();
  });
});

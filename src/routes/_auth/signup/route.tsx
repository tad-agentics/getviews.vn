import { Navigate } from "react-router";

/** OAuth-only product — account creation goes through login. */
export default function SignupRedirect() {
  return <Navigate to="/login" replace />;
}

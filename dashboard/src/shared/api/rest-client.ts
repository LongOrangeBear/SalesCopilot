/**
 * REST API клиент.
 */
import { useCallback } from "react";
import { API_URL } from "./config";

export function useApi() {
  const fetchApi = useCallback(async <T>(endpoint: string): Promise<T> => {
    const resp = await fetch(`${API_URL}${endpoint}`);
    if (!resp.ok) throw new Error(`API Error: ${resp.status}`);
    return resp.json();
  }, []);

  return { fetchApi, apiUrl: API_URL };
}

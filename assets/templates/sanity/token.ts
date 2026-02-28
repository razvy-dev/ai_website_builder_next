import { client } from "./client";

export const token = process.env.SANITY_VIEWER_TOKEN;

export function getClient() {
  return client;
}

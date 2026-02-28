import { defineLive } from "next-sanity/live";

export const { SanityLive, useLive } = defineLive({
  client: import("./client").then((mod) => mod.client),
});

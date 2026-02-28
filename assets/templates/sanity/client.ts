import { createClient } from "next-sanity";

export const client = createClient({
  projectId: process.env.NEXT_PUBLIC_SANITY_PROJECT_ID,
  dataset: process.env.NEXT_PUBLIC_SANITY_DATASET,
  apiVersion: process.env.NEXT_PUBLIC_SANITY_API_VERSION || "2024-12-01",
  useCdn: true,
  token: process.env.SANITY_VIEWER_TOKEN,
  stega: {
    studioUrl: process.env.NEXT_PUBLIC_SANITY_STUDIO_URL,
  },
});

export const urlFor = (source: any) => {
  if (!source) return null;
  try {
    return builder.image(source);
  } catch {
    return null;
  }
};

import { createImageUrlBuilder } from "next-sanity";
const builder = createImageUrlBuilder(client);

import { client } from "./client";
import { draftMode } from "next/headers";

export async function sanityFetch<T>({
  query,
  params = {},
  tags,
}: {
  query: string;
  params?: Record<string, unknown>;
  tags?: string[];
}): Promise<T> {
  const { isEnabled } = await draftMode();

  if (isEnabled) {
    return client.fetch<T>(query, params, {
      perspective: "previewDrafts",
      useCdn: false,
      stega: true,
      next: { revalidate: 0, tags },
    });
  }

  return client.fetch<T>(query, params, {
    next: { tags },
  });
}

import { sanityFetch } from "@/sanity/lib/fetch";
import { defineQuery } from "next-sanity";

const QUERY = defineQuery(`*[_type == "page"][0]`);

export default async function HomePage() {
  const data = await sanityFetch<{ title?: string; _id?: string }>({
    query: QUERY,
  });

  return (
    <main>
      <h1>{data?.title || "Welcome"}</h1>
      <p>Page ID: {data?._id}</p>
    </main>
  );
}

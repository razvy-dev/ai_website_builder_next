from pathlib import Path


SANITY_CLIENT_TEMPLATE = """import { createClient } from "next-sanity";

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
"""

TOKEN_HELPER_TEMPLATE = """import { client } from "./client";

export const token = process.env.SANITY_VIEWER_TOKEN;

export function getClient() {
  return client;
}
"""

ENABLE_DRAFT_MODE_TEMPLATE = """import { defineEnableDraftMode } from "next-sanity/draft-mode";
import { client } from "@/sanity/lib/client";
import { token } from "@/sanity/lib/token";

export const { GET } = defineEnableDraftMode({
  client: client.withConfig({ token }),
});
"""

DISABLE_DRAFT_MODE_TEMPLATE = """import { defineDisableDraftMode } from "next-sanity/draft-mode";
import { client } from "@/sanity/lib/client";

export const { GET } = defineDisableDraftMode({ client });
"""

DISABLE_DRAFT_MODE_COMPONENT_TEMPLATE = """"use client";

import { useDraftModeEnvironment } from "next-sanity/hooks";
import { useRouter } from "next/navigation";

export function DisableDraftMode() {
  const environment = useDraftModeEnvironment();
  const router = useRouter();

  if (environment !== "live" && environment !== "unknown") {
    return null;
  }

  return (
    <button
      onClick={() => {
        router.push("/api/draft-mode/disable");
      }}
      style={{
        position: "fixed",
        bottom: "20px",
        right: "20px",
        padding: "10px 20px",
        background: "#000",
        color: "#fff",
        border: "none",
        borderRadius: "5px",
        cursor: "pointer",
        zIndex: 9999,
      }}
    >
      Exit Draft Mode
    </button>
  );
}
"""

LAYOUT_TEMPLATE = """import { VisualEditing } from "next-sanity/visual-editing";
import { draftMode } from "next/headers";
import { DisableDraftMode } from "@/components/DisableDraftMode";
import { SanityLive } from "@/sanity/lib/live";
import "./globals.css";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        {children}
        {(await draftMode()).isEnabled && (
          <>
            <DisableDraftMode />
            <VisualEditing />
          </>
        )}
        <SanityLive />
      </body>
    </html>
  );
}
"""

SANITY_LIVE_TEMPLATE = """import { defineLive } from "next-sanity/live";

export const { SanityLive, useLive } = defineLive({
  client: import("./client").then((mod) => mod.client),
});
"""

SANITY_CONFIG_TEMPLATE = """import { defineConfig } from "sanity";
import { structureTool } from "sanity/structure";
import { presentationTool } from "sanity/presentation";

export default defineConfig({
  name: "{project_name}",
  title: "{project_title}",
  projectId: process.env.SANITY_PROJECT_ID,
  dataset: process.env.SANITY_DATASET || "production",
  basePath: "/studio",
  plugins: [
    structureTool(),
    presentationTool({
      previewUrl: {
        origin: process.env.SANITY_STUDIO_PREVIEW_ORIGIN || "http://localhost:3000",
        preview: "/",
        previewMode: {
          enable: "/api/draft-mode/enable",
          disable: "/api/draft-mode/disable",
        },
      },
    }),
  ],
});
"""


def create_sanity_client(output_dir: Path) -> None:
    """Create Sanity client with stega for Visual Editing."""
    src_dir = output_dir / "frontend" / "src" / "sanity" / "lib"
    src_dir.mkdir(parents=True, exist_ok=True)

    (src_dir / "client.ts").write_text(SANITY_CLIENT_TEMPLATE)
    print(f"  Created: {src_dir / 'client.ts'}")

    (src_dir / "token.ts").write_text(TOKEN_HELPER_TEMPLATE)
    print(f"  Created: {src_dir / 'token.ts'}")


def create_live_mode(output_dir: Path) -> None:
    """Create Sanity Live configuration."""
    src_dir = output_dir / "frontend" / "src" / "sanity" / "lib"
    src_dir.mkdir(parents=True, exist_ok=True)

    (src_dir / "live.ts").write_text(SANITY_LIVE_TEMPLATE)
    print(f"  Created: {src_dir / 'live.ts'}")


def create_draft_mode_routes(output_dir: Path) -> None:
    """Create enable/disable draft mode API routes."""
    api_dir = output_dir / "frontend" / "src" / "app" / "api" / "draft-mode"
    api_dir.mkdir(parents=True, exist_ok=True)

    (api_dir / "enable" / "route.ts").write_text(ENABLE_DRAFT_MODE_TEMPLATE)
    print(f"  Created: {api_dir / 'enable' / 'route.ts'}")

    (api_dir / "disable" / "route.ts").write_text(DISABLE_DRAFT_MODE_TEMPLATE)
    print(f"  Created: {api_dir / 'disable' / 'route.ts'}")


def create_disable_draft_mode_component(output_dir: Path) -> None:
    """Create the Disable Draft Mode button component."""
    components_dir = output_dir / "frontend" / "src" / "components"
    components_dir.mkdir(parents=True, exist_ok=True)

    (components_dir / "DisableDraftMode.tsx").write_text(
        DISABLE_DRAFT_MODE_COMPONENT_TEMPLATE
    )
    print(f"  Created: {components_dir / 'DisableDraftMode.tsx'}")


def update_layout(output_dir: Path) -> None:
    """Update root layout with Visual Editing components."""
    layout_path = output_dir / "frontend" / "src" / "app" / "layout.tsx"

    if layout_path.exists():
        layout_path.write_text(LAYOUT_TEMPLATE)
        print(f"  Updated: {layout_path}")
    else:
        print(f"  Warning: {layout_path} not found, skipping layout update")


def create_sanity_config(output_dir: Path, project_name: str) -> None:
    """Create Sanity config with Presentation tool."""
    studio_dir = output_dir / "studio"

    config_path = studio_dir / "sanity.config.ts"

    config_content = SANITY_CONFIG_TEMPLATE.format(
        project_name=project_name.lower().replace(" ", "-"),
        project_title=project_name,
    )

    config_path.write_text(config_content)
    print(f"  Created: {config_path}")


def install_dependencies(output_dir: Path) -> None:
    """Install required npm packages for Visual Editing."""
    import subprocess

    frontend_dir = output_dir / "frontend"

    print("\nInstalling npm packages...")

    packages = ["next-sanity@latest", "@sanity/client", "@sanity/visual-editing"]

    for pkg in packages:
        try:
            subprocess.run(
                ["npm", "install", pkg],
                cwd=frontend_dir,
                check=True,
            )
            print(f"  Installed: {pkg}")
        except subprocess.CalledProcessError as e:
            print(f"  Warning: Failed to install {pkg}: {e}")


def setup_visual_editing(output_dir: Path, project_name: str) -> None:
    """Main function to set up all Visual Editing components."""
    print("\nSetting up Visual Editing...")

    create_sanity_client(output_dir)
    create_live_mode(output_dir)
    create_draft_mode_routes(output_dir)
    create_disable_draft_mode_component(output_dir)
    update_layout(output_dir)
    create_sanity_config(output_dir, project_name)

    print("\nVisual Editing setup complete!")

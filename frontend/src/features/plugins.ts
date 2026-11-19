/**
 * Discovery of optional feature plugins.
 *
 * A feature adds a single `plugin.ts` file under `src/features/<id>/` and is
 * picked up automatically by the router and the module launcher. No shared
 * registry needs to be edited, which keeps parallel branches conflict free.
 */

import type { ComponentType } from "react";

/** Description of a feature module contributed by a branch. */
export interface FeaturePlugin {
  /** Stable identifier, used as the React key and for sorting. */
  id: string;
  /** Human readable label shown in navigation. */
  label: string;
  /** Browser path served by the plugin. */
  path: string;
  /** Short description shown in the module launcher. */
  description: string;
  /** Group used to cluster modules in the launcher. */
  group: string;
  /** Root component rendered for the plugin route. */
  component: ComponentType;
}

/** Shape of a module discovered by Vite. */
interface PluginModule {
  plugin: FeaturePlugin;
}

const modules = import.meta.glob<PluginModule>("./*/plugin.ts", {
  eager: true,
});

/**
 * Remove duplicates and sort plugins by identifier.
 *
 * @param plugins - Raw plugin declarations.
 * @returns A stable, unique list of plugins.
 */
export function normalizePlugins(plugins: FeaturePlugin[]): FeaturePlugin[] {
  const seen = new Set<string>();
  const unique = plugins.filter((plugin) => {
    if (!plugin.id || seen.has(plugin.id)) return false;
    seen.add(plugin.id);
    return true;
  });
  return unique.sort((a, b) => a.id.localeCompare(b.id));
}

/**
 * Return every discovered feature plugin in a stable order.
 *
 * @returns The sorted plugins.
 */
export function discoverPlugins(): FeaturePlugin[] {
  const found = Object.values(modules)
    .map((module) => module.plugin)
    .filter((plugin): plugin is FeaturePlugin => Boolean(plugin));
  return normalizePlugins(found);
}

/**
 * Find the plugin whose route matches a pathname.
 *
 * @param pathname - The current browser path.
 * @returns The matching plugin, when one exists.
 */
export function pluginForPath(pathname: string): FeaturePlugin | undefined {
  return discoverPlugins().find(
    (plugin) =>
      pathname === plugin.path || pathname.startsWith(`${plugin.path}/`),
  );
}

/**
 * Group plugins by their declared group name.
 *
 * @param plugins - The plugins to group.
 * @returns A mapping of group name to its plugins.
 */
export function groupPlugins(
  plugins: FeaturePlugin[],
): Record<string, FeaturePlugin[]> {
  const grouped: Record<string, FeaturePlugin[]> = {};
  for (const plugin of plugins) {
    const key = plugin.group || "Modules";
    grouped[key] = [...(grouped[key] ?? []), plugin];
  }
  return grouped;
}

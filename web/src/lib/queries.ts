/**
 * TanStack Query hooks over `api.ts`, adapted to the view types the
 * console's components already render.
 *
 * Adaptation happens IN the hook, not in the component: a component
 * asking `useDetections()` should get slick features back, not a wire
 * object it then has to know how to translate. Keeping that translation
 * out of Shell.tsx is what keeps Shell.tsx readable as a layout, not a
 * mapping exercise.
 */

import { useQuery } from "@tanstack/react-query";

import { detectionToSlickFeature, shipDetectionToShipPoint, tracksFromApi } from "./adapters";
import { getSuspects, listAisTracks, listDetections, listShips } from "./api";
import type { ShipPoint, SlickFeature, VesselTrack } from "./fixtures";

export function useDetections(sceneId?: string) {
  return useQuery({
    queryKey: ["detections", sceneId],
    queryFn: async (): Promise<SlickFeature[]> => {
      const detections = await listDetections({ scene_id: sceneId });
      return detections.map(detectionToSlickFeature);
    },
  });
}

export function useShips(sceneId?: string) {
  return useQuery({
    queryKey: ["ships", sceneId],
    queryFn: async (): Promise<ShipPoint[]> => {
      const ships = await listShips(sceneId);
      return ships.map(shipDetectionToShipPoint);
    },
  });
}

/**
 * Every AIS track for the scene, joined with suspect rankings for the
 * given detection. If `detectionId` is undefined (nothing selected yet),
 * tracks still load — just with no suspect ranking to join against, so
 * every vessel renders as ordinary AIS traffic until a detection is
 * selected.
 */
export function useTracks(detectionId?: string) {
  return useQuery({
    queryKey: ["tracks", detectionId],
    queryFn: async (): Promise<VesselTrack[]> => {
      const [tracks, suspects] = await Promise.all([
        listAisTracks(),
        detectionId ? getSuspects(detectionId) : Promise.resolve([]),
      ]);
      return tracksFromApi(tracks, suspects);
    },
  });
}

/** Ranked suspects for a detection, factors and all — including the
 *  negative (exculpatory) contributions, which are never filtered. */
export function useSuspects(detectionId: string | undefined) {
  return useQuery({
    queryKey: ["suspects", detectionId],
    queryFn: () => getSuspects(detectionId as string),
    enabled: detectionId !== undefined,
  });
}

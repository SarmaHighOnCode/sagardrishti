/**
 * The client types must match the server's published schema.
 *
 * This is the test that stops a frontend change from quietly inventing a
 * field the API never sends. It reads `docs/api/openapi.json` — generated
 * from `services/api/app/schemas.py` by `tools/export_openapi.py` and kept
 * fresh by CI — so it checks against what the server actually publishes,
 * not against a second hand-written copy of the same assumptions.
 *
 * No running API is needed. That matters: a contract check only people
 * with the stack up can run is a contract check that stops being run.
 */

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { CONTRACT, NOT_MIRRORED } from "./contract";

interface OpenApiProperty {
  default?: unknown;
}

interface OpenApiSchema {
  properties?: Record<string, OpenApiProperty>;
  required?: string[];
}

const spec = JSON.parse(
  readFileSync(new URL("../../../docs/api/openapi.json", import.meta.url), "utf-8"),
) as { components: { schemas: Record<string, OpenApiSchema> } };

const serverSchemas = spec.components.schemas;

/**
 * Field names the server declares, and which of them a client can count
 * on being present.
 *
 * `required` in OpenAPI answers "must the caller SEND this?", which is
 * not the question a response consumer is asking. These are response
 * models — the API accepts no request bodies at all — so the useful
 * question is "will the server always EMIT this?", and the two differ for
 * any field with a default: Pydantic leaves it out of `required` but
 * serialises it every time.
 *
 * Hence: required, or defaulted to something other than null. A `null`
 * default is the genuinely absent case (`sog_knots: float | None = None`)
 * and stays optional. Verified against live responses — `data_quality`
 * defaults to "ok" and appears on every point the API returns.
 */
function serverFields(name: string): { all: string[]; alwaysPresent: Set<string> } {
  const schema = serverSchemas[name];
  const properties = schema.properties ?? {};
  const required = new Set(schema.required ?? []);

  const alwaysPresent = new Set(
    Object.entries(properties)
      .filter(([field, prop]) => required.has(field) || (prop.default ?? null) !== null)
      .map(([field]) => field),
  );

  return { all: Object.keys(properties), alwaysPresent };
}

describe("client types match the server's OpenAPI schema", () => {
  it.each(Object.keys(CONTRACT))("%s exists on the server", (name) => {
    // A client type with no server counterpart is unverifiable, and
    // historically that is where drift hides.
    expect(Object.keys(serverSchemas)).toContain(name);
  });

  it.each(Object.entries(CONTRACT))("%s has no invented fields", (name, client) => {
    const server = serverFields(name);
    const invented = Object.keys(client).filter((f) => !server.all.includes(f));

    // These would be `undefined` at runtime, silently. A panel bound to
    // one renders blank rather than failing, which is the worst outcome:
    // it looks like "no data" instead of "wrong field name".
    expect(invented, `${name}: field(s) not on the server`).toEqual([]);
  });

  it.each(Object.entries(CONTRACT))("%s is not missing server fields", (name, client) => {
    const server = serverFields(name);
    const missing = server.all.filter((f) => !(f in client));

    expect(missing, `${name}: server sends field(s) the client does not model`).toEqual([]);
  });

  it.each(Object.entries(CONTRACT))("%s agrees on what is optional", (name, client) => {
    const server = serverFields(name);

    const disagreements = Object.entries(client)
      .filter(([field]) => server.all.includes(field))
      .map(([field, optionality]) => {
        const serverSays = server.alwaysPresent.has(field) ? "required" : "optional";
        return serverSays === optionality
          ? null
          : `${field}: client ${optionality}, server ${serverSays}`;
      })
      .filter((d): d is string => d !== null);

    // The dangerous direction is client "required" / server "optional":
    // the code will dereference a field the server may legitimately omit,
    // and it will work for every record until the one that doesn't have it.
    expect(disagreements, `${name}: optionality mismatch`).toEqual([]);
  });

  it("mirrors every server schema, or excludes it deliberately", () => {
    const unaccounted = Object.keys(serverSchemas).filter(
      (name) => !(name in CONTRACT) && !NOT_MIRRORED.some((p) => p.test(name)),
    );

    // A new server type appearing unnoticed is the drift this whole file
    // exists to catch. Mirror it in apiTypes.ts + contract.ts, or add it
    // to NOT_MIRRORED with a reason — but decide, don't ignore.
    expect(unaccounted, "server schema neither mirrored nor excluded").toEqual([]);
  });
});

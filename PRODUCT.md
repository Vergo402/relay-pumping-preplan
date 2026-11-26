# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- Fire officers and chauffeurs (engine drivers and pump operators) of Yorktown Heights Fire District (YHFD).
- Members of other Westchester County fire districts can use the page. They select their district.
- The users are firefighters. They are not developers.
- Use 1, pre-plan: a user plans a long supply hose lay for a known address before an incident. There is no time pressure.
- Use 2, on scene: a user opens the page during an incident to get the hose length, the relay engine positions, and the pump pressures. Time is short.
- During the pilot, Alex Vergo is the primary user and the owner.

Open decision: the role of the on-scene user (officer, chauffeur, or other) is not recorded.

## Product Purpose

The page plans a supply hose lay for a long driveway that climbs a hill.
The user enters an address. The page drafts a hose route from the nearest hydrant by road. The user corrects the route.
The page reads the ground height along the route. It then shows the hose to lay, the climb, the relay engines, each engine position, and each pump discharge pressure (PDP).
It shows 500, 750, and 1,000 GPM together. It also makes a one-page pre-plan card to print.

Success: the numbers agree with the YHFD chauffeur chart and with the results that the chauffeurs get in the field.

## Positioning

The page joins three things for one address: the real ground height, the real hydrant positions, and the department hydraulic rules.
A paper chart gives the pressure for a hose length. It does not know the hill or the hydrant.

## Operating Context

- The work has three parts: Find (screen the district for problem driveways), Calculate (this page), and Carry (printed cards). Only Calculate is built.
- The printed pre-plan card is a product output. Crews can read the card in the field.
- The page opens as a file from a folder. Alex keeps his copy in a OneDrive folder.
- The page needs an internet connection for maps, address search, roads, and ground height.
- Screens: a desktop or laptop computer, and a phone. A tablet is not a stated need.

## Capabilities and Constraints

- The tool stays one HTML file. No server, no login, and no hosting.
- The tool uses free public data only: Westchester County GIS and USGS. No paid service and no account key.
- The hydraulic rules come from the YHFD chauffeur reference chart. They apply to all districts in the page.
- The tool is a planning aid. Each screen and each card tells the user to verify on site.
- The page does not know the flow of a hydrant or a draft site. The hydrant data is from 2015.
- The road draft uses hydrants only. It makes no draft when no hydrant is in 1 mile by road.
- A change to the hydraulic rules, the defaults, or the data needs approval from Alex.
- Terms: supply line, reverse lay, forward lay, relay engine, attack engine, water source, PDP, LDH, GPM, PSI, chauffeur.
- Status: pilot v0.4. No field check is done yet.

- The built-in start values are the YHFD values: 1,000 ft of hose on each engine and 185 PSI maximum PDP. A YHFD engine carries 1,500 ft, and the department maximum is 200 PSI.
- A user can set their own start values. The values stay in the browser or in a saved copy of the page.

## Brand Commitments

- Name: YHFD Relay Pumping Calculator.
- Voice: plain language that a firefighter uses. No developer terms on the screen.
- Documents use ASD-STE100 Simplified Technical English.

## Evidence on Hand

- The YHFD chauffeur reference chart (PDF) is the source of the hydraulic values. The math checks in `tests/test_core.js` compare the page with it.
- County data: 60 fire district boundaries and 22,499 hydrants, in `data/`.
- An accepted mockup for v0.3 is in `docs/mockups/`.
- No field check results, no user feedback from other members, and no photos exist yet. Do not invent them.

## Product Principles

1. The numbers must be correct and must show their source. A wrong pre-plan is worse than no pre-plan.
2. The page states its limits. It never shows a draft or a result as a verified fact.
3. The user controls the route. The page drafts, and the user corrects.
4. On scene, the answer comes first: hose, engines, positions, and pressures.
5. The tool stays simple to keep and to share: one file, public data, plain words.

# Addresses and Geocoding

`RIRAddress` holds a structured postal address: street address, city, state/province, postal code and country. The plugin uses it in two places:

- **Synced records**: organizations, contacts and customers synced from the RIR keep their address as an `RIRAddress`. Identical addresses are shared, since the five address fields are unique together.
- **Site addresses**: a NetBox Site can have one site-level `RIRAddress`, which supplies the customer address for a simple reassignment.

Addresses are listed under **RIR Manager > Addresses**, where they can also be added and edited by hand.

## The RIR Address panel on a Site

Every Site detail page gets an **RIR Address** panel. It shows the site-level address, whether it was **Geocoded** or entered by hand (**Manual**), and when it was last resolved. The pencil button edits the address.

**Resolve** opens a dialog of up to five candidate addresses:

1. With latitude and longitude on the Site, the plugin reverse-geocodes the coordinates. Nominatim returns a single candidate for a reverse lookup.
2. Otherwise, or when that finds nothing, it geocodes the Site's physical address.
3. The search field takes any other address to look up instead.

**Select** on a candidate saves it as the Site's address and marks it as geocoded. It replaces any existing site-level address for that Site.

## Where Site addresses are used

- **Reassign form on a Prefix**: the customer address fields are pre-filled from the address of the prefix's Site, when it has one. See [Reassigning a prefix](write-operations.md#reassigning-a-prefix).
- **Automatic simple reassignment**: the job uses the Site's address. When the Site has none, the job geocodes one from the Site's coordinates or physical address and saves it. When that fails, the job stops with the error `Could not resolve address for site`. See [Automatic reassignment and removal](write-operations.md#automatic-reassignment-and-removal).

The state/province is stored as the ISO 3166-2 subdivision code without the country prefix (`QC`, `NY`, `NW`) and the country as the ISO 3166-1 two-letter code, which is what ARIN expects. When geocoding, the plugin finds the subdivision code in this order:

1. The ISO 3166-2 code Nominatim returns for the state level (for example `DE-NW` for North Rhine-Westphalia, stored as `NW`).
2. The state or province name compared, ignoring case, with the subdivision names in `pycountry`, both the local-language name (`Nordrhein-Westfalen`) and its English name where `pycountry` has one (`Bavaria`).
3. The ISO 3166-2 code Nominatim returns for the next level down, when it has one.

When none of these gives a code, the address is not saved, and the error reads `Could not determine the ISO 3166-2 subdivision code for '<name>'; enter it on the Site's RIR address.`:

- In the Resolve dialog, the candidate shows that error and has no **Select** button.
- An automatic simple reassignment that has to geocode the address records `status: error` and that message in its job data and writes an `error` sync log, without creating a customer or submitting the reassignment to ARIN.

In both cases, add or edit the Site's address by hand under **RIR Manager > Addresses** with the subdivision code, then retry. The state/province field holds at most 10 characters; a longer value is refused with a message asking for the code, there and on the manual Reassign form.

## Geocoding provider

Geocoding uses OpenStreetMap Nominatim through `geopy`, identifying itself with the user agent `netbox-rir-manager`. It is the only provider; the `geocoding_provider` setting has no other value today (see [Settings](../reference/settings.md)).

The plugin calls Nominatim only on demand: when someone opens or searches the Resolve dialog, and when an automatic simple reassignment needs an address for a Site that has none. A saved address is reused and never geocoded again. Keep within the [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/), which limits the public service to light use.

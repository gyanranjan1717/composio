# Labelling rubric

This is the single definition of every field. The research agent, the verifier agent and the
human labelling the gold sample all read this same file, so an answer means the same thing
whoever produced it.

Judge every field from the vendor's own documentation or official pages. Blog posts, forum
answers and third-party directories are not evidence, except for `existingMcp = community`.

## authMethods (list, every method the vendor documents for its public API)

- `oauth2`: any OAuth 2.0 flow (authorization code, client credentials, PKCE).
- `apiKey`: any static secret a user or admin generates in a dashboard and sends with each
  request. This includes API keys, personal access tokens, bot tokens, and key + secret pairs.
- `basic`: HTTP Basic auth, including "email + API token" sent as Basic.
- `jwt`: the caller signs its own JWT (service account, key-pair auth).
- `other`: a documented scheme that fits none of the above (for example AWS SigV4).
- `none`: there is no authentication because there is no hosted API (local CLI tools).

## oauthAppReviewRequired (true / false)

True only if the docs say an OAuth app or API access must pass a vendor review or approval
before it can be used with other customers' production data.

## accessLevel (one value: the cheapest route for an independent developer to get working credentials)

- `selfServeFree`: sign up and get credentials on a free account, free tier or free developer
  sandbox, with no human approval.
- `selfServeTrial`: possible only through a time-limited free trial of a paid product.
- `paidPlan`: API access needs a paid plan, but it can be bought online without talking to sales.
- `adminApproval`: sign-up is open, but usable credentials need a vendor review or approval
  step (app review, developer-token application, access request form).
- `partnerGated`: you must contact sales, be an existing enterprise customer, or join a partner
  programme.
- `noPublicApi`: no public API exists.

## apiType

`rest`, `graphql`, `restAndGraphql`, `cliOnly` (a command-line tool or library, no hosted API),
`other` (for example SOAP or SQL-only), `none`.

## apiBreadth

- `broad`: read and write across most of the product's core objects.
- `medium`: several resources, but clear gaps (read-only, or major objects missing).
- `narrow`: one resource or a handful of endpoints.
- `none`: no API.

## existingMcp

- `official`: the vendor publishes or hosts an MCP server. Put its docs or repo URL in `mcpUrl`.
- `community`: only third-party MCP servers exist. Put one URL in `mcpUrl`.
- `none`: no MCP server found. `mcpUrl` is an empty string.

## buildable (could Composio ship an agent toolkit for this today?)

- `yes`: documented API and credentials are obtainable self-serve.
- `partial`: it can be built, but something limits it (review step, paid plan, narrow API).
- `no`: it cannot be built from public information.

## mainBlocker (the single biggest obstacle; `none` when buildable is `yes`)

`none`, `partnerOrSalesGate`, `paidPlanRequired`, `appReviewRequired`, `adminApprovalRequired`,
`noPublicApi`, `notAnApi` (a CLI or library, not a service), `thinOrMissingDocs`, `narrowApi`,
`other`.

## evidence

At least one entry for each of `authMethods`, `accessLevel`, `apiType`, `existingMcp`. Each entry
has the `url` of the page and a `quote` copied word for word from that page (under 300
characters) that supports the answer. Never paraphrase a quote. If a page could not be opened,
do not cite it.

For `existingMcp = none` and `accessLevel = noPublicApi`, cite the page that was checked and
quote the nearest relevant sentence; absence cannot be quoted directly.

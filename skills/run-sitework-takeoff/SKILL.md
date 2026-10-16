---
name: run-sitework-takeoff
description: Run a sitework takeoff with the Land Takeoffs MCP tools. Use when the user wants quantities, cut and fill, or an Excel bid sheet from a civil plan-set PDF or a DWG, DXF or LandXML file.
---

# Run a sitework takeoff with Land Takeoffs

Use the `land-takeoffs` MCP server tools. Never invent a quantity; report only what the tools return.

## Steps

1. **Check credits (optional).** `check_balance` shows credits left. A takeoff costs 1 credit (plan sets: 1 credit per 100 pages). Failed takeoffs are not charged.
2. **Get the files to the server.**
   - Files are links (Dropbox, Google Drive, OneDrive or SharePoint, or a direct https link anyone with the link can open): pass them to a start tool.
   - Files are on the user's computer: call `get_upload_link` and give the user the private link (valid 24 hours, one takeoff). Do not try to read or upload the files yourself.
3. **Ask before CAD takeoffs.** If a CAD file is included, ask for topsoil strip depth (inches), shrink percent (from the geotech report) and the share of stripped topsoil reused as fill. Pass what the user knows. If they skip shrink, none is applied and the report says so.
4. **Start the takeoff.**
   - Plan set and/or CAD together: `start_takeoff`
   - Plan-set PDF only: `start_plan_set_takeoff`
   - CAD or terrain files only: `start_cad_takeoff`
   - Optional: `list_price_lists`, then pass `price_list` so the Excel workbook is priced (prices appear in the Excel only).
5. **Answer questions.** If a start tool returns a question (for example two possible site boundaries, or which surface is existing ground), ask the user and pass the choice to `answer_cad_question`.
6. **Wait.** Call `get_takeoff_status` with the `takeoff_id` every 30 to 60 seconds until it succeeds or fails. Takeoffs usually take a few minutes.
7. **Report results.** `get_takeoff_results` returns lines by division with the source sheet or file and a confidence level. Tell the user the source sheet for each quantity and list every line that could not be determined, with the reason.
8. **Deliverables.** `get_download_links` returns the Excel bid sheet and PDF summary. For takeoffs that include a CAD file it also returns the project video, still images, a download-all zip and a 3D viewer link once they finish rendering; call again if they are still rendering. Links expire, so call again for fresh ones.

## Notes

- `list_takeoffs` shows recent takeoffs; `get_upload_page` returns the account page.
- The video, images and 3D viewer are rendered from the takeoff data. They are not AI-generated.
- Results should be reviewed by a qualified estimator before bidding.

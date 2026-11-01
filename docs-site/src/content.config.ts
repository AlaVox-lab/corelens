// SPDX-License-Identifier: MIT
// Copyright (c) 2026 AlaVox-lab
//
// Bộ sưu tập nội dung của trang tài liệu: mọi trang nằm ở `src/content/docs/`.

import { docsLoader } from "@astrojs/starlight/loaders";
import { docsSchema } from "@astrojs/starlight/schema";
import { defineCollection } from "astro:content";

export const collections = {
  docs: defineCollection({ loader: docsLoader(), schema: docsSchema() }),
};

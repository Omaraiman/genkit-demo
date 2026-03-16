# ── Windows / Pydantic compatibility patch ────────────────────────────────────
import pydantic.json_schema as _pjs

_orig_handle_invalid = _pjs.GenerateJsonSchema.handle_invalid_for_json_schema

def _safe_handle_invalid(self, schema, error_info):
    return {}

_pjs.GenerateJsonSchema.handle_invalid_for_json_schema = _safe_handle_invalid
# ── End patch ─────────────────────────────────────────────────────────────────

from typing import Optional
from pydantic import BaseModel, Field
from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI
from dotenv import load_dotenv
import os

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

load_dotenv()

ai = Genkit(
    plugins=[GoogleAI(api_key=os.getenv('GEMINI_API'))],
    model='googleai/gemini-2.5-flash',
)

app = FastAPI(title="Product SEO Generator API")

# Mount static files directory
# Make sure to create a "static" folder in the same directory as main.py
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Input Schema ──────────────────────────────────────────────────────────────

class ProductInput(BaseModel):
    product_name: str = Field(description='اسم المنتج — أول حاجة في العنوان دايماً')
    brand_name: Optional[str] = Field(default=None, description='اسم الشركة المصنعة')
    key_features: str = Field(description='المكونات والمميزات الأساسية مفصولة بفواصل')
    flavor_or_variant: Optional[str] = Field(default=None, description='النكهة أو الحجم')
    target_audience: Optional[str] = Field(default=None, description='الجمهور المستهدف')
    usage_instructions: Optional[str] = Field(default=None, description='طريقة الاستخدام')
    warnings: Optional[str] = Field(default=None, description='تحذيرات خاصة')
    category_hint: Optional[str] = Field(default=None, description='تلميح للكاتيجوري')
    nutritional_info: Optional[str] = Field(default=None, description='القيم الغذائية لو متاحة')

# ── Output Schema ─────────────────────────────────────────────────────────────

class ProductSEOContent(BaseModel):
    # Arabic fields
    ar_seo_meta_title: str = Field(description='عنوان SEO بالعربي — اسم المنتج أولاً، أقل من 60 حرف')
    ar_full_description_html: str = Field(description='الوصف الكامل HTML بالعربي — لا يقل عن 1500 كلمة بعناوين H2/H3 كاملة')
    ar_short_description: str = Field(description='وصف مختصر بالعربي — 2-3 جمل تسويقية')
    ar_meta_description: str = Field(description='Rank Math Meta Description بالعربي — 150-160 حرف')
    ar_focus_keyword: str = Field(description='الكلمة المفتاحية الأساسية بالعربي')
    ar_product_tags: list[str] = Field(description='5-10 وسوم بالعربي — قصيرة وقوية فقط')
    ar_suggested_category: str = Field(description='الكاتيجوري المقترحة بالعربي')

    # English fields
    en_seo_meta_title: str = Field(description='SEO Meta Title in English — product name first, under 60 chars')
    en_full_description_html: str = Field(description='Full HTML description in English — min 1500 words with H2/H3 structure exactly like the reference sample provided')
    en_short_description: str = Field(description='Short description in English — 2-3 punchy marketing sentences')
    en_meta_description: str = Field(description='Rank Math Meta Description in English — 150-160 chars')
    en_focus_keyword: str = Field(description='Primary focus keyword in English')
    en_product_tags: list[str] = Field(description='5-10 English tags — short and strong only')
    en_suggested_category: str = Field(description='Suggested category in English')

    # Shared
    compliance_note: str = Field(description='Google Merchant + Ads + Facebook compliance check — one paragraph')


# ── Prompt Builder ────────────────────────────────────────────────────────────

def build_prompt(inp: ProductInput) -> str:
    variant_line   = f'Flavor / Variant: {inp.flavor_or_variant}' if inp.flavor_or_variant else ''
    brand_line     = f'Brand (never put first in title): {inp.brand_name}' if inp.brand_name else ''
    audience_line  = f'Target Audience: {inp.target_audience}' if inp.target_audience else ''
    usage_line     = f'Usage Instructions: {inp.usage_instructions}' if inp.usage_instructions else ''
    warnings_line  = f'Warnings: {inp.warnings}' if inp.warnings else ''
    nutrition_line = f'Nutritional Info per serving: {inp.nutritional_info}' if inp.nutritional_info else ''
    hint_line      = f'Category Hint: {inp.category_hint}' if inp.category_hint else ''

    categories_list = """
Sports Nutrition > Build Muscle > Amino acids > BCAA & Recovery
Sports Nutrition > Build Muscle > Amino acids > Creatine
Sports Nutrition > Build Muscle > Protein
Sports Nutrition > Electrolytes & Hydration
Sports Nutrition > Fat Burners
Sports Nutrition > Mass Gainers & Carbs
Sports Nutrition > Pre Workout & Testosterone Booster > Pre Workout
Sports Nutrition > Protein Bars & Snacks > Protein Bars
Sports Nutrition > Protein Bars & Snacks > Protein Shake
Vitamins & Health > Bone & Joint Health
Vitamins & Health > Brain & Cognitive Health > Memory & Focus Support
Vitamins & Health > Brain & Cognitive Health > Mood & Sleep
Vitamins & Health > Omegas
Vitamins & Health > General Health > Gut Health & Digestion
Vitamins & Health > General Health > Herbal Extracts
Vitamins & Health > General Health > Immunity Health
Vitamins & Health > General Health > Men's Health
Vitamins & Health > General Health > Minerals
Vitamins & Health > Vitamins > Multivitamins
Vitamins & Health > Vitamins > Single Vitamins
Vitamins & Health > Women's Health > Hair, Nail & Skin
Vitamins & Health > Women's Health > Women's Vitamins
Vitamins & Health > Weight Loss > Blood Sugar Support
Vitamins & Health > Weight Loss > Fiber supplement
Healthy Food & Beverage > Cereals
Healthy Food & Beverage > Snacks
Healthy Food & Beverage > Super Foods
Beauty & Personal Care > Skin Care > Moisturizers
Beauty & Personal Care > Hair Care > Shampoo
Beauty & Personal Care > Body Care > Body Lotions
"""

    # Reference HTML sample so the model knows EXACTLY what format we want
    reference_html_structure = """
REFERENCE HTML STRUCTURE (follow this exact pattern for both Arabic and English):

<h2>Why Athletes Choose [Product Name]?</h2>
<p>Opening marketing paragraph...</p>
<p>Second paragraph about who uses it and why...</p>
<p>Third paragraph bridging to benefits...</p>
<hr />

<h2>What Is [Product Name]?</h2>
<p>Definition paragraph...</p>
<p>Context in sports nutrition...</p>
<ul>
  <li><p>Use case 1</p></li>
  <li><p>Use case 2</p></li>
  <li><p>Use case 3</p></li>
</ul>
<hr />

<h2>Key Benefits of [Product Name]</h2>
<h3>1. Benefit Title</h3>
<p>Explanation...</p>
<h3>2. Benefit Title</h3>
<p>Explanation...</p>
(5-7 benefits total)
<hr />

<h2>❓ Frequently Asked Questions</h2>
<h3>Question one?</h3>
<p>Answer...</p>
<h3>Question two?</h3>
<p>Answer...</p>
(4-6 questions from People Also Ask)
<hr />

<h2>🍽️ Suggested Preparation / How to Use</h2>
<p>Intro sentence...</p>
<ol>
  <li><p>Step 1</p></li>
  <li><p>Step 2</p></li>
  <li><p>Step 3</p></li>
</ol>
<p>Optional additions:</p>
<ul>
  <li><p>Addition 1</p></li>
  <li><p>Addition 2</p></li>
</ul>
<hr />

<h2>🌿 Ingredients</h2>
<p>Intro...</p>
<ul>
  <li><p><strong>Ingredient 1</strong> — explanation of its role</p></li>
  <li><p><strong>Ingredient 2</strong> — explanation of its role</p></li>
</ul>
<hr />

<h2>⚡ What Makes [Product Name] Different?</h2>
<p>Intro sentence...</p>
<ul>
  <li><p>Differentiator 1</p></li>
  <li><p>Differentiator 2</p></li>
</ul>
<hr />

<h2>🕒 Best Time to Use [Product Name]</h2>
<p>Context paragraph...</p>
<ul>
  <li><p>Timing 1</p></li>
  <li><p>Timing 2</p></li>
</ul>
<hr />

<h2>🧾 Product Details</h2>
<ul>
  <li><p>Product Type: ...</p></li>
  <li><p>Form: ...</p></li>
  <li><p>Net Weight: ...</p></li>
  <li><p>Serving Size: ...</p></li>
  <li><p>Servings Per Container: ...</p></li>
</ul>
<p>Approximate nutritional values per serving:</p>
<ul>
  <li><p>Calories: ...</p></li>
  <li><p>Protein: ...</p></li>
  <li><p>Carbohydrates: ...</p></li>
  <li><p>Fat: ...</p></li>
</ul>
<hr />

<h2>⚠️ Important Notes</h2>
<ul>
  <li><p>Note 1</p></li>
  <li><p>Note 2</p></li>
</ul>
<hr />

<h2>👨‍⚕️ Nutrition Expert Tip</h2>
<p>Expert advice paragraph 1...</p>
<p>Expert advice paragraph 2...</p>
<hr />

<h2>🔔 Call to Action</h2>
<p>Closing motivational paragraph with CTA...</p>
"""

    return f"""You are a senior SEO content strategist and sports nutrition specialist working for a leading health e-commerce brand.

Your task: Write COMPLETE, PROFESSIONAL product page content for a WordPress WooCommerce site using Rank Math SEO plugin.
The content must be delivered in BOTH Arabic AND English simultaneously.
Goal: Maximum organic search visibility + high conversion rate + full compliance with Google Merchant Center, Google Ads, and Facebook Ads policies.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRODUCT INFORMATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Product Name (Primary Focus Keyword): {inp.product_name}
{brand_line}
{variant_line}
Key Features / Ingredients: {inp.key_features}
{audience_line}
{usage_line}
{nutrition_line}
{warnings_line}
{hint_line}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HTML STRUCTURE — FOLLOW EXACTLY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{reference_html_structure}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT CONTENT RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. WORD COUNT: Full description must be minimum 1500 words per language.

2. FOCUS KEYWORD DENSITY:
   - Use "{inp.product_name}" naturally between 4 and 6 times in the full description.
   - Never stuff it. Never drop below 4 or exceed 6 occurrences.

3. PRODUCT NAME IN TITLES:
   - "{inp.product_name}" must always be the FIRST word(s) in SEO titles.
   - Never start with the brand name.

4. GOOGLE MERCHANT CENTER + ADS + FACEBOOK ADS COMPLIANCE (CRITICAL):
   - ❌ BANNED words: "treats", "cures", "heals", "prevents disease", "يعالج", "يشفي", "علاج", "وقاية من مرض"
   - ✅ ALLOWED phrases: "supports", "contributes to", "designed to", "may help", "يدعم", "يساهم في", "مصمم لـ", "قد يساعد"
   - No direct medical claims. No targeting personal hardships or medical conditions.
   - Keep all claims benefit-oriented and general, not disease-specific.

5. HTML TAGS:
   - Use proper semantic HTML: <h2>, <h3>, <p>, <ul>, <ol>, <li>, <strong>, <hr />
   - Wrap every <li> content in <p> tags (as shown in reference)
   - Use <hr /> between major sections
   - Use emoji icons before H2 section titles where appropriate

6. SEO TAGS (5-10 only per language):
   - Short and strong: product name, active ingredient, category, target audience
   - NO long-tail keywords as tags — embed those inside the content instead

7. ARABIC CONTENT:
   - Formal Arabic (فصحى مبسطة) — professional, warm, credible tone
   - Short digestible paragraphs
   - People Also Ask questions must feel natural in Arabic search context

8. ENGLISH CONTENT:
   - Follow the exact HTML structure of the reference sample above
   - Professional, clean, athlete-oriented tone
   - People Also Ask questions from real Google searches

9. Never mention or hint that content is AI-generated.

10. LSI & LONG-TAIL KEYWORDS:
    - Embed them naturally inside paragraphs and H2/H3 titles
    - Do NOT use them as product tags

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AVAILABLE CATEGORIES (choose the best fit):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{categories_list}

Deliver ALL fields in both languages as specified in the output schema."""


# ── Flow ──────────────────────────────────────────────────────────────────────

@ai.flow()
async def product_seo_generator(input_data: ProductInput) -> ProductSEOContent:
    prompt = build_prompt(input_data)

    result = await ai.generate(
        prompt=prompt,
        output_schema=ProductSEOContent,
    )

    if not result.output:
        raise ValueError('فشل توليد المحتوى')

    output = result.output
    if isinstance(output, dict):
        output = ProductSEOContent(**output)

    return output


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.post("/api/generate", response_model=ProductSEOContent)
async def generate_seo_content(input_data: ProductInput):
    try:
        content = await product_seo_generator(input_data)
        if isinstance(content, dict):
             return ProductSEOContent(**content)
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
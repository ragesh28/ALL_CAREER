import registry from './practiceCompanyBrands.json';

// Official website metadata from Wikidata, plus reviewed company sites and brand icons.
const domains = new Map(Object.entries(registry.domains));
const images = new Map(Object.entries(registry.images));

export function getPracticeCompanyBrand(name: string) {
  const key = name.normalize('NFKD').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');
  const domain = domains.get(key);
  return domain ? { domain, image: images.get(key) } : undefined;
}

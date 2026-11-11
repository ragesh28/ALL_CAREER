import { calculateWalkinFacets, WalkinFacetInput } from './walkinFacets';

self.onmessage = ({ data }: MessageEvent<WalkinFacetInput>) => {
  self.postMessage(calculateWalkinFacets(data));
};

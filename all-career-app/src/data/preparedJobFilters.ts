export const JOBS_PER_PAGE = 50;

export const PREPARED_CITIES = [
  'bangalore', 'chennai', 'hyderabad', 'mumbai', 'delhi',
  'pune', 'noida', 'kolkata', 'ahmedabad', 'remote',
];

export const PREPARED_SOURCES = [
  'linkedin', 'naukri', 'indeed', 'internshala', 'glassdoor', 'shine',
  'timesjobs', 'hirist', 'workindia', 'foundit', 'apna', 'freshersworld',
];

export function preparedJobFilterKey(source: string, city: string, exactZero: boolean) {
  return source + '/' + city + '/software_technical/' + (exactZero ? 'exact-zero' : 'zero');
}

export function preparedRoleFilterKey(source: string, city: string, role: string, exactZero: boolean) {
  return source + '/' + city + '/role/' + encodeURIComponent(role) + '/' + (exactZero ? 'exact-zero' : 'zero');
}

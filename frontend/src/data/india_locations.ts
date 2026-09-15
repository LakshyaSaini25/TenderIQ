/**
 * Complete list of all Indian States + Union Territories with their major cities.
 * Used for the location-based source discovery feature in the Sources page.
 */

export interface IndiaState {
  name: string;
  cities: string[];
}

export const INDIA_STATES: IndiaState[] = [
  {
    name: "Andhra Pradesh",
    cities: [
      "Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Kurnool",
      "Rajahmundry", "Tirupati", "Kakinada", "Kadapa", "Anantapur",
      "Vizianagaram", "Eluru", "Ongole", "Nandyal", "Machilipatnam",
      "Adoni", "Tenali", "Proddatur", "Chittoor", "Hindupur",
    ],
  },
  {
    name: "Arunachal Pradesh",
    cities: [
      "Itanagar", "Naharlagun", "Pasighat", "Tawang", "Ziro",
      "Bomdila", "Along", "Tezu", "Roing", "Aalo",
    ],
  },
  {
    name: "Assam",
    cities: [
      "Guwahati", "Silchar", "Dibrugarh", "Jorhat", "Nagaon",
      "Tinsukia", "Tezpur", "Bongaigaon", "Dhubri", "Diphu",
      "North Lakhimpur", "Sivasagar", "Goalpara", "Barpeta", "Karimganj",
      "Haflong", "Mangaldoi", "Hojai",
    ],
  },
  {
    name: "Bihar",
    cities: [
      "Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Purnia",
      "Darbhanga", "Bihar Sharif", "Arrah", "Begusarai", "Katihar",
      "Munger", "Chhapra", "Danapur", "Bettiah", "Motihari",
      "Hajipur", "Jehanabad", "Sitamarhi", "Saharsa", "Siwan",
      "Sasaram", "Nawada", "Kishanganj", "Aurangabad",
    ],
  },
  {
    name: "Chhattisgarh",
    cities: [
      "Raipur", "Bhilai", "Bilaspur", "Korba", "Durg",
      "Rajnandgaon", "Jagdalpur", "Raigarh", "Ambikapur", "Dhamtari",
      "Chirmiri", "Bhatapara", "Mahasamund", "Kanker",
    ],
  },
  {
    name: "Goa",
    cities: [
      "Panaji", "Vasco da Gama", "Margao", "Mapusa", "Ponda",
      "Bicholim", "Curchorem", "Sanquelim", "Pernem",
    ],
  },
  {
    name: "Gujarat",
    cities: [
      "Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar",
      "Jamnagar", "Junagadh", "Gandhinagar", "Anand", "Navsari",
      "Morbi", "Nadiad", "Surendranagar", "Bharuch", "Mehsana",
      "Bhuj", "Porbandar", "Palanpur", "Valsad", "Amreli",
      "Gandhidham", "Botad", "Patan", "Veraval",
    ],
  },
  {
    name: "Haryana",
    cities: [
      "Faridabad", "Gurugram", "Panipat", "Ambala", "Yamunanagar",
      "Rohtak", "Hisar", "Karnal", "Sonipat", "Panchkula",
      "Bhiwani", "Sirsa", "Bahadurgarh", "Jind", "Thanesar",
      "Kaithal", "Palwal", "Rewari", "Narnaul", "Hansi",
    ],
  },
  {
    name: "Himachal Pradesh",
    cities: [
      "Shimla", "Solan", "Dharamsala", "Mandi", "Palampur",
      "Baddi", "Nahan", "Kullu", "Hamirpur", "Una",
      "Chamba", "Bilaspur", "Kangra", "Manali", "Sundarnagar",
    ],
  },
  {
    name: "Jharkhand",
    cities: [
      "Ranchi", "Jamshedpur", "Dhanbad", "Bokaro", "Deoghar",
      "Hazaribagh", "Giridih", "Ramgarh", "Chaibasa", "Medininagar",
      "Chirkunda", "Phusro", "Dumka", "Gumla", "Simdega",
    ],
  },
  {
    name: "Karnataka",
    cities: [
      "Bengaluru", "Mysuru", "Hubballi", "Mangaluru", "Belagavi",
      "Kalaburagi", "Ballari", "Vijayapura", "Shimoga", "Tumkur",
      "Raichur", "Bidar", "Davanagere", "Hassan", "Udupi",
      "Dharwad", "Chikkamagaluru", "Chitradurga", "Mandya", "Bagalkot",
      "Gangavati", "Gadag", "Hosapete", "Robertsonpet",
    ],
  },
  {
    name: "Kerala",
    cities: [
      "Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam",
      "Kannur", "Malappuram", "Palakkad", "Alappuzha", "Kottayam",
      "Kasaragod", "Idukki", "Pathanamthitta", "Wayanad", "Munnar",
      "Ponnani", "Tirur", "Manjeri",
    ],
  },
  {
    name: "Madhya Pradesh",
    cities: [
      "Indore", "Bhopal", "Jabalpur", "Gwalior", "Ujjain",
      "Sagar", "Dewas", "Satna", "Ratlam", "Rewa",
      "Murwara", "Singrauli", "Burhanpur", "Khandwa", "Bhind",
      "Chhindwara", "Guna", "Shivpuri", "Vidisha", "Chhatarpur",
      "Damoh", "Mandsaur", "Khargone", "Neemuch", "Pithampur",
    ],
  },
  {
    name: "Maharashtra",
    cities: [
      "Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad",
      "Solapur", "Amravati", "Kolhapur", "Thane", "Navi Mumbai",
      "Pimpri-Chinchwad", "Akola", "Latur", "Dhule", "Ahmednagar",
      "Chandrapur", "Jalgaon", "Bhiwandi", "Nanded", "Malegaon",
      "Sangli", "Jalna", "Ulhasnagar", "Ratnagiri", "Satara",
      "Wardha", "Ichalkaranji", "Osmanabad", "Parbhani", "Beed",
    ],
  },
  {
    name: "Manipur",
    cities: [
      "Imphal", "Thoubal", "Bishnupur", "Churachandpur", "Senapati",
      "Ukhrul", "Tamenglong", "Jiribam",
    ],
  },
  {
    name: "Meghalaya",
    cities: [
      "Shillong", "Tura", "Jowai", "Nongstoin", "Baghmara",
      "Cherrapunji", "Williamnagar",
    ],
  },
  {
    name: "Mizoram",
    cities: [
      "Aizawl", "Lunglei", "Champhai", "Serchhip", "Kolasib",
      "Lawngtlai", "Mamit",
    ],
  },
  {
    name: "Nagaland",
    cities: [
      "Kohima", "Dimapur", "Mokokchung", "Tuensang", "Wokha",
      "Zunheboto", "Mon", "Phek",
    ],
  },
  {
    name: "Odisha",
    cities: [
      "Bhubaneswar", "Cuttack", "Rourkela", "Brahmapur", "Sambalpur",
      "Puri", "Balasore", "Bhadrak", "Baripada", "Jharsuguda",
      "Bargarh", "Angul", "Dhenkanal", "Kendujhar", "Sundargarh",
      "Paradip", "Kendrapara", "Rayagada",
    ],
  },
  {
    name: "Punjab",
    cities: [
      "Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda",
      "Mohali", "Hoshiarpur", "Batala", "Pathankot", "Moga",
      "Abohar", "Malerkotla", "Khanna", "Phagwara", "Muktsar",
      "Barnala", "Rajpura", "Firozpur",
    ],
  },
  {
    name: "Rajasthan",
    cities: [
      "Jaipur", "Jodhpur", "Kota", "Bikaner", "Ajmer",
      "Udaipur", "Bhilwara", "Alwar", "Bharatpur", "Sikar",
      "Pali", "Sri Ganganagar", "Tonk", "Chittorgarh", "Barmer",
      "Jaisalmer", "Jhunjhunu", "Nagaur", "Hanumangarh", "Bundi",
      "Sawai Madhopur", "Dholpur", "Dungarpur", "Churu",
    ],
  },
  {
    name: "Sikkim",
    cities: [
      "Gangtok", "Namchi", "Gyalshing", "Mangan", "Rangpo",
    ],
  },
  {
    name: "Tamil Nadu",
    cities: [
      "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem",
      "Tirunelveli", "Vellore", "Erode", "Thoothukudi", "Tiruppur",
      "Dindigul", "Thanjavur", "Ranipet", "Sivakasi", "Karur",
      "Udhagamandalam", "Hosur", "Nagercoil", "Kanchipuram", "Kumbakonam",
      "Cuddalore", "Nagapattinam", "Ramanathapuram", "Namakkal",
    ],
  },
  {
    name: "Telangana",
    cities: [
      "Hyderabad", "Warangal", "Nizamabad", "Khammam", "Karimnagar",
      "Ramagundam", "Mahabubnagar", "Nalgonda", "Adilabad", "Suryapet",
      "Siddipet", "Miryalaguda", "Jagtial", "Mancherial", "Kothagudem",
      "Bhongir", "Secunderabad",
    ],
  },
  {
    name: "Tripura",
    cities: [
      "Agartala", "Dharmanagar", "Udaipur", "Kailasahar", "Belonia",
      "Sabroom", "Ambassa",
    ],
  },
  {
    name: "Uttar Pradesh",
    cities: [
      "Lucknow", "Kanpur", "Ghaziabad", "Agra", "Meerut",
      "Varanasi", "Prayagraj", "Bareilly", "Aligarh", "Moradabad",
      "Saharanpur", "Gorakhpur", "Noida", "Firozabad", "Jhansi",
      "Muzaffarnagar", "Mathura", "Shahjahanpur", "Rampur", "Faizabad",
      "Hapur", "Ayodhya", "Etawah", "Bulandshahr", "Sitapur",
      "Loni", "Mirzapur", "Hardoi", "Orai", "Sambhal",
    ],
  },
  {
    name: "Uttarakhand",
    cities: [
      "Dehradun", "Haridwar", "Roorkee", "Haldwani", "Rudrapur",
      "Kashipur", "Rishikesh", "Manglaur", "Kotdwara", "Pithoragarh",
      "Nainital", "Mussoorie", "Almora",
    ],
  },
  {
    name: "West Bengal",
    cities: [
      "Kolkata", "Asansol", "Siliguri", "Durgapur", "Bardhaman",
      "Malda", "Barasat", "Krishnanagar", "Habra", "Kharagpur",
      "Haldia", "Raiganj", "Jalpaiguri", "Bankura", "Purulia",
      "Midnapore", "Balurghat", "Alipurduar", "Contai", "Darjeeling",
    ],
  },

  // ── Union Territories ───────────────────────────────────────────────────
  {
    name: "Delhi",
    cities: [
      "New Delhi", "Delhi", "Dwarka", "Rohini", "Pitampura",
      "Janakpuri", "Saket", "Lajpat Nagar", "Karol Bagh", "Shahdara",
      "Noida Extension", "Faridabad", "Gurugram",
    ],
  },
  {
    name: "Chandigarh",
    cities: ["Chandigarh", "Panchkula", "Mohali"],
  },
  {
    name: "Jammu and Kashmir",
    cities: [
      "Srinagar", "Jammu", "Anantnag", "Baramulla", "Sopore",
      "Pampore", "Leh", "Kupwara", "Pulwama", "Udhampur",
    ],
  },
  {
    name: "Ladakh",
    cities: ["Leh", "Kargil"],
  },
  {
    name: "Puducherry",
    cities: ["Puducherry", "Karaikal", "Yanam", "Mahe"],
  },
  {
    name: "Andaman and Nicobar Islands",
    cities: ["Port Blair", "Car Nicobar"],
  },
  {
    name: "Lakshadweep",
    cities: ["Kavaratti"],
  },
  {
    name: "Dadra and Nagar Haveli and Daman and Diu",
    cities: ["Silvassa", "Daman", "Diu"],
  },
];

/** Returns sorted state names for the dropdown */
export const STATE_NAMES: string[] = INDIA_STATES.map(s => s.name).sort();

/** Returns cities for a given state name */
export function getCitiesForState(stateName: string): string[] {
  const state = INDIA_STATES.find(s => s.name === stateName);
  return state ? ["All Cities", ...state.cities.sort()] : [];
}


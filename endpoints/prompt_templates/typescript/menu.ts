// TODO: Recipes, e.g. Cinnamon Dolce Latte
// TODO: default quantity for syrups depends on size
// TODO: no powders for Brewed Coffes and Caffe Misto
// TODO: decide whether to make options, quantity, size, etc. optional or allow Default.
//       Depends on how complicated the fixup algorithm is.
//       Can make dictionary from `name` to template object with default values.
// TODO: Decide whether tea lattes belong with coffee lattes.
// TODO: Iced Teas, Tea Frappuccino, Refreshers, Frappuccinos, Hot Chocolate, Lemonade, Bottled, Traveler

type Cart = { items: Item[] };

type Item =
  | HotBrewedCoffee
  | HotMilkCoffee
  | HotEspresso
  | ColdCoffee
  | HotBrewedTea
  | BakeryItem
// | IcedTea;

type BakeryItem = {
  name: "Blueberry Streusel Muffin";
  quantity: number;
  options?: BakeryOption[];
};

type BakeryOption = BooleanOption<"Warmed">;

// TODO: Brewed coffee options do no include Powders
type HotBrewedCoffee = {
  name:
    | "Brewed Roast - Sunsera"
    | LITERAL<
        "Medium Roast - Pike Place Roast",
        ["coffee", "drip", "joe"],
        false
      >
    | "Dark Roast - Sumatra"
    | LITERAL<
        "Decaf Roast - Pike Place Roast",
        ["coffee", "drip", "joe", "unleaded"],
        false
      >;
  quantity: number;
  size?: HotSize;
  options?: (Creamer | HotMilkOptions | EspressoOptions | GeneralOptions)[];
};

// TODO: no Powders for Caffè Misto
// TODO: Americano does not have MilkBase
type HotMilkCoffee = {
  name:
    | "Caffè Misto"
    | "Americano"
    | "Cappuccino"
    | "Caffè Mocha"
    | "White Chocolate Mocha"
    | "Latte"
    | "Cinnamon Dolce Latte"
    | "Starbucks Blonde Vanilla Latte"
    | "Lavender Oatmilk Latte"
    | "Caramel Macchiato"
    | "Flat White"
    | "Cortado";
  quantity: number;
  milk?: MilkBase | Default;
  size?: HotSize;
  options?: (HotMilkOptions | EspressoOptions | GeneralOptions)[];
};

type HotEspresso = {
  name: "Espresso" | "Espresso Con Pannaa" | "Espresso Macchiato";
  quantity: number;
  size?: EspressoSize;
  options?: (EspressoOptions | GeneralOptions)[];
};

type ColdCoffee =
  | ColdBrew
  | IcedShaken
  | IcedMilkCoffee
  | NitroColdBrew
  | IcedEspresso;

type ColdBrew = {
  name:
    | "Iced Coffee"
    | "Cold Brew"
    | "Raspberry Cream Cold Brew"
    | "Vanilla Sweet Cream Cold Brew"
    | "Salted Caramel Cream Cold Brew"
    | "Chocolate Cream Cold Brew"
    | "Nondairy Vanilla Sweet Cream Cold Brew"
    | "Nondairy Salted Caramel Cream Cold Brew"
    | "Cold Brew with Nondairy Vanilla Sweet Cream Cold Foam"
    | "Nondairy Chocolate Cream Cold Brew";
  quantity: number;
  size?: ColdBrewSize;
  options?: (EspressoOptions | GeneralOptions | RaspberryPearls)[];
};

type IcedShaken = {
  name:
    | "Iced Shaken Espresso"
    | "Iced Horchata Oatmilk Shaken Espresso"
    | "Iced Brown Sugar OatmilkShaken Espresso"
    | "Iced Hazelnut Oatmilk Shaken Espresso";
  quantity: number;
  size?: ColdSize;
  milk?: MilkBase | Default;
  options?: (EspressoOptions | GeneralOptions | RaspberryPearls)[];
};

// TODO: Americano does not have MilkBase
// TODO: verify that tea lattes work here
type IcedMilkCoffee = {
  name:
    | "Iced Americano"
    | "Iced Latte"
    | "Iced Caffè Mocha"
    | "Iced White Chocolate Mocha"
    | "Iced Caramel Macchiato"
    | "Iced Flat White"
    | "Iced Cinnamon Dolce Latte"
    | "Iced Starbucks Blonde Vanilla Latte"
    | "Iced Lavender Oatmilk Latte"
    | "Iced Caramel Macchiato"
    | "Chai Latte"
    | "Matcha Latte"
    | "London Fog Latte";
  quantity: number;
  milk?: MilkBase | Default;
  size?: ColdSize;
  options?: (EspressoOptions | GeneralOptions)[];
};

type NitroColdBrew = {
  name: "Nitro Cold Brew" | "Vanilla Sweet Cream Nitro Cold Brew";
  size?: NitroColdBrewSize;
  options?: (EspressoOptions | GeneralOptions | RaspberryPearls)[];
};

type IcedEspresso = {
  name: "Iced Espresso";
  quantity: number;
  size?: EspressoSize;
  options?: (EspressoOptions | GeneralOptions)[];
};

// TODO: Lemonade is only available to Honey Citrus Mint Tea
type HotBrewedTea = {
  name:
    | "Honey Citrus Mint Tea"
    | "Royal English Breakfast Tea"
    | "Emperor's Clouds and Mist Tea"
    | "Mint Majesty Tea"
    | "Earl Grey Tea"
    | "Chamomile Mint Blossom Tea";
  quantity: number;
  size?: HotSize;
  options?: (
    | TeaBags
    | Option<"Lemonade">
    | Powders
    | Syrups
    | Sweeteners
    | Toppings
    | Cups
  )[];
};

// TODO: Iced Teas, Tea Frappuccino, Refreshers, Frappuccinos, Hot Chocolate, Lemonade, Bottled, Traveler
type IcedTea = { name: "Foobar" };

type HotMilkOptions = Foam | MilkTemperature;

type Foam = Option<"Foam">;

type MilkTemperature = BooleanOption<"Extra Hot" | "Steamed Hot" | "Warm">;

type EspressoOptions = Caffeine | Shots;

// TODO: Matcha Powder is only available for Tea Lattes.
type GeneralOptions =
  | BooleanOption<
      "Line the Cup with Caramel Sauce" | "Line the Cup with Mocha Sauce"
    >
  | Tea
  | Powders
  | Sauces
  | Syrups
  | Sweeteners
  | ColdFoam
  | Toppings
  | Cups
  | Option<"Ice" | "Water" | "Room">
  | DiscreteOption<"Matcha Powder">;

type MilkBase =
  | "2% Milk"
  | "Almond"
  | "Breve (Half & Half)"
  | "Coconut"
  | "Heavy Cream"
  | "Nondairy Vanilla Sweet Cream"
  | LITERAL<"Nonfat Milk", ["skinny", "skim"], false>
  | LITERAL<"Oatmilk", ["oat"], false>
  | "Soy"
  | "Vanilla Sweet Cream"
  | "Whole Milk";

type Creamer = Option<
  | "Splash of 2% Milk"
  | "Splash of Coconut Milk"
  | "Splash of Cream (Half & Half)"
  | "Splash of Heavy Cream"
  | "Splash of Nondairy Vanilla Sweet Cream"
  | LITERAL<"Splash of Nonfat Milk", ["skinny", "skim"], false>
  | LITERAL<"Splash of Oatmilk", ["oat"], false>
  | LITERAL<"Splash of Soymilk", ["soy"], false>
  | "Splash of Vanilla Sweet Cream"
  | "Splash of Whole Milk"
>;

type Caffeine = BooleanOption<
  | LITERAL<
      "1/2 Decaf",
      ["half", "caf", "caffeinated", "decaf", "decaffeinated"],
      false
    >
  | LITERAL<
      "1/3 Decaf",
      ["third", "caf", "caffeinated", "decaf", "decaffeinated"],
      false
    >
  | LITERAL<
      "2/3 Decaf",
      ["third", "caf", "caffeinated", "decaf", "decaffeinated"],
      false
    >
  | "Blonde Espresso"
  | LITERAL<
      "Decaf Espresso Roast",
      ["caf", "caffeinated", "decaf", "decaffeinated", "unleaded"],
      false
    >
  | "Signature Espresso"
>;

type Shots =
  | DiscreteOption<"Shots">
  | BooleanOption<"Long Shot" | "Ristretto" | "Upside Down">;

type Tea = DiscreteOption<"Pump(s) Chai">;

type TeaBags = DiscreteOption<"Tea Bag(s)">;

type Powders = Option<
  | "Cherry Sweet Powder"
  | "Chocolate Malt Powder"
  | "Lavender Powder"
  | "Vanilla Bean Powder"
>;

type Sauces = DiscreteOption<
  "Dark Caramel Sauce" | "Mocha Sauce" | "White Chocolate Mocha Sauce"
>;

type Syrups = Option<
  | "Brown Sugar Syrup"
  | "Caramel Syrup"
  | "Cinnamon Dolce Syrup"
  | "Hazelnut Syrup"
  | "Honey Blend Syrup"
  | "Horchata Syrup"
  | "Peppermint Syrup"
  | "Raspberry Syrup"
  | "Sugar-free Vanilla Syrup"
  | "Vanilla Syrup"
>;

type Sweeteners = DiscreteOption<
  | "Classic Syrup"
  | "Packet(s) Honey"
  | "Packet(s) Stevia in the Raw"
  | "Packet(s) Sugar"
  | "Packet(s) Sugar in the Raw"
>;

type ColdFoam = Option<
  | "Brown Sugar Cream Cold Foam"
  | "Cherry Cream Cold Foam"
  | "Choclate Cream Cold Foam"
  | "Horchata Cream Cold Foam"
  | "Lavender Cream Cold Foam"
  | "Match Cream Cold Foam"
  | "Raspberry Cream Cold Foam"
  | "Salted Caramel Cream Cold Foam"
  | "Strawberry Cream Cold Foam"
  | "Vanilla Sweet Cream Cold Foam"
  | "Nondairy Brown Sugar Cold Foam"
  | "Nondairy Chocolate Cream Cold Foam"
  | "Nondairy Matcha Cream Cold Foam"
  | "Nondairy Salted Caramel Cream Cold Foam"
  | "Nondairy Strawberry Cream Cold Foam"
  | "Nondairy Vanilla Sweet Cream Cold Foam"
>;

type Toppings = Option<
  | "Cinnamon Powder"
  | "Caramel Drizzle"
  | "Mocha Drizzle"
  | "Whipped Cream"
  | "Caramel Crunch Topping"
  | "Cinnamon Dolce Sprinkles"
  | "Cookie Crumble Topping"
>;

type Cups = BooleanOption<
  "Grande Cup" | "Short Cup" | "Tall Cup" | "Venti Cup" | "Personal Cup"
>;

type RaspberryPearls = DiscreteOption<"Raspberry Pearls">;

type Option<NAME> = {
  name: NAME;
  amount?: Amount;
};

type DiscreteOption<NAME> = {
  name: NAME;
  quantity: number;
};

type BooleanOption<NAME> = {
  name: NAME;
};

type Amount = "Extra" | "Light" | "No" | LITERAL<"Regular", [], true>;

type HotSize = "Short" | "Tall" | LITERAL<"Grande", [], true> | "Venti";
type IcedCoffeeSize = "Tall" | LITERAL<"Grande", [], true> | "Venti" | "Trenta";
type NitroColdBrewSize = "Tall" | LITERAL<"Grande", [], true>;
type ColdBrewSize = "Tall" | LITERAL<"Grande", [], true> | "Venti" | "Trenta";
type ColdSize = "Tall" | LITERAL<"Grande", [], true> | "Venti";
type EspressoSize = "Solo" | LITERAL<"Doppio", [], true> | "Triple" | "Quad";

type Default = "DEFAULT";

// Hint: Use CHOOSE when customer doesn't specify an option and the option is not specified by a template literal
type CHOOSE = LITERAL<"CHOOSE", [], true>;

type LITERAL<NAME, ALIASES, IS_OPTIONAL> = NAME;

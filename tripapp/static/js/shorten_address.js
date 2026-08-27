function shortenAddress(result) {
    var props = result.properties || {};
    var addr = props.address || {};

    var street = [addr.house_number, addr.road].filter(Boolean).join(' ');
    var city = addr.city || addr.town || addr.village || addr.municipality || '';

    if (street && city) {
        return `${street}, ${city}`;
    }
    if (street) {
        return street;
    }
    if (city) {
        return city;
    }

    // Fallback
    if (result.name) {
        return result.name.split(',').slice(0, 2).join(',').trim();
    }

    return '';
}
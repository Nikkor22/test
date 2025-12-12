public class Task6 {

    public static void main(String[] args) {
        int n = 10;
        System.out.println("Первые " + n + " членов гармонического ряда:");
        System.out.println(" i |   1/i");
        System.out.println("---------------");

        for (int i = 1; i <= n; i++) {
            double term = 1.0 / i;
            System.out.printf("%2d | %8.6f%n", i, term); // 6 знаков после запятой
        }
    }
}
